"""
analytics_engine.py - Graph Analytics Dashboard Engine

Phase 2 Task #31: Visual insights from the knowledge graph

Features:
- Skill progression timeline
- Company comparison matrix
- Topic network graph
- Interview frequency calendar
- Performance trends

Usage:
    from analytics_engine import analytics
    skill_data = analytics.get_skill_progression("user_id", "Python")
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("analytics_engine")

# Import cognitive graph
try:
    from cognitive_graph import cognitive_graph, query_graph
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False
    logger.warning("[Analytics] Cognitive graph not available")


class AnalyticsEngine:
    """
    Generate analytics and insights from the cognitive graph.
    """

    def __init__(self):
        self.graph = cognitive_graph if COGNITIVE_GRAPH_AVAILABLE else None

    def get_skill_progression(
        self,
        user_id: str,
        skill_name: str,
        months: int = 6
    ) -> Dict:
        """
        Get skill progression over time.

        Returns data points showing confidence/mentions over months.
        """
        if not self.graph or not self.graph.driver:
            return {"error": "Cognitive graph not available"}

        try:
            # Query for skill mentions over time
            cypher = """
            MATCH (i:Interview {user_id: $user_id})-[:CONTAINS]->(q:Question)
                  -[:ANSWERED_WITH]->(a:Answer)-[:DEMONSTRATES]->(s:Skill {name: $skill})
            RETURN i.timestamp as date, a.confidence as proficiency, q.text as context
            ORDER BY i.timestamp
            """

            with self.graph.driver.session() as session:
                result = session.run(cypher, user_id=user_id, skill=skill_name)
                records = [dict(r) for r in result]

            # Group by month
            monthly_data = defaultdict(lambda: {"mentions": 0, "avg_confidence": 0.0, "contexts": []})

            for record in records:
                if record.get("date"):
                    date_key = record["date"].strftime("%Y-%m") if hasattr(record["date"], "strftime") else str(record["date"])[:7]
                    monthly_data[date_key]["mentions"] += 1
                    monthly_data[date_key]["avg_confidence"] += record.get("proficiency", 0.7)
                    monthly_data[date_key]["contexts"].append(record.get("context", "")[:100])

            # Calculate averages and format
            data_points = []
            for month, data in sorted(monthly_data.items()):
                if data["mentions"] > 0:
                    data["avg_confidence"] /= data["mentions"]

                data_points.append({
                    "month": month,
                    "mentions": data["mentions"],
                    "confidence": round(data["avg_confidence"], 2),
                    "trend": "improving" if data["avg_confidence"] > 0.7 else "stable",
                    "sample_questions": data["contexts"][:3]
                })

            # Calculate trend
            if len(data_points) >= 2:
                first_conf = data_points[0]["confidence"]
                last_conf = data_points[-1]["confidence"]
                overall_trend = last_conf - first_conf
            else:
                overall_trend = 0

            return {
                "skill": skill_name,
                "user_id": user_id,
                "data_points": data_points,
                "total_mentions": sum(d["mentions"] for d in data_points),
                "current_confidence": data_points[-1]["confidence"] if data_points else 0,
                "overall_trend": round(overall_trend, 2),
                "trend_direction": "up" if overall_trend > 0.1 else "down" if overall_trend < -0.1 else "stable"
            }

        except Exception as e:
            logger.error("[Analytics] Skill progression error: %s", str(e))
            return {"error": "An internal error occurred"}

    def get_company_comparison(self, companies: List[str]) -> Dict:
        """
        Compare interview patterns across companies.

        Returns heatmap data of question categories by company.
        """
        if not self.graph or not self.graph.driver:
            return {"error": "Cognitive graph not available"}

        try:
            comparison = {}

            for company in companies:
                cypher = """
                MATCH (c:Company {name: $company})<-[:ASKED_BY]-(q:Question)
                RETURN q.category as category, count(q) as count,
                       collect(DISTINCT q.difficulty) as difficulties
                """

                with self.graph.driver.session() as session:
                    result = session.run(cypher, company=company)
                    categories = {r["category"]: r["count"] for r in result}

                comparison[company] = {
                    "categories": categories,
                    "total_questions": sum(categories.values()),
                    "top_category": max(categories, key=categories.get) if categories else None
                }

            # Create heatmap matrix
            all_categories = set()
            for data in comparison.values():
                all_categories.update(data["categories"].keys())

            heatmap = []
            for company in companies:
                row = []
                for category in sorted(all_categories):
                    count = comparison[company]["categories"].get(category, 0)
                    total = comparison[company]["total_questions"]
                    percentage = (count / total * 100) if total > 0 else 0
                    row.append({
                        "count": count,
                        "percentage": round(percentage, 1)
                    })
                heatmap.append({
                    "company": company,
                    "values": row
                })

            return {
                "companies": companies,
                "categories": sorted(all_categories),
                "heatmap": heatmap,
                "comparison": comparison
            }

        except Exception as e:
            logger.error("[Analytics] Company comparison error: %s", str(e))
            return {"error": "An internal error occurred"}

    def get_topic_network(self, user_id: str, min_connections: int = 2) -> Dict:
        """
        Get topic co-occurrence network for visualization.

        Returns nodes (topics) and edges (co-occurrences).
        """
        if not self.graph or not self.graph.driver:
            return {"error": "Cognitive graph not available"}

        try:
            # Get topic co-occurrences
            cypher = """
            MATCH (i:Interview {user_id: $user_id})-[:CONTAINS]->(q:Question)
                  -[:RELATED_TO]->(t1:Topic)
            MATCH (q)-[:RELATED_TO]->(t2:Topic)
            WHERE t1 <> t2
            RETURN t1.name as topic1, t2.name as topic2, count(*) as weight
            ORDER BY weight DESC
            LIMIT 100
            """

            with self.graph.driver.session() as session:
                result = session.run(cypher, user_id=user_id)
                connections = [dict(r) for r in result]

            # Build network
            nodes = {}
            edges = []

            for conn in connections:
                t1, t2, weight = conn["topic1"], conn["topic2"], conn["weight"]

                # Add nodes
                for topic in [t1, t2]:
                    if topic not in nodes:
                        nodes[topic] = {
                            "id": topic,
                            "name": topic,
                            "group": self._categorize_topic(topic),
                            "connections": 0
                        }
                    nodes[topic]["connections"] += weight

                # Add edge
                if weight >= min_connections:
                    edges.append({
                        "source": t1,
                        "target": t2,
                        "weight": weight
                    })

            # Filter nodes with few connections
            active_nodes = {k: v for k, v in nodes.items() if v["connections"] >= min_connections}

            # Calculate node sizes based on connections
            max_connections = max(n["connections"] for n in active_nodes.values()) if active_nodes else 1
            for node in active_nodes.values():
                node["size"] = 10 + (node["connections"] / max_connections * 30)

            return {
                "nodes": list(active_nodes.values()),
                "edges": edges,
                "total_topics": len(nodes),
                "active_topics": len(active_nodes),
                "strongest_connection": max(edges, key=lambda x: x["weight"]) if edges else None
            }

        except Exception as e:
            logger.error("[Analytics] Topic network error: %s", str(e))
            return {"error": "An internal error occurred"}

    def _categorize_topic(self, topic: str) -> str:
        """Categorize topic for coloring in network graph"""
        topic_lower = topic.lower()

        categories = {
            "frontend": ["react", "javascript", "css", "html", "dom", "vue", "angular"],
            "backend": ["api", "database", "server", "backend", "microservices"],
            "algorithms": ["algorithm", "sorting", "tree", "graph", "complexity"],
            "system_design": ["system design", "distributed", "scalability", "load balancer"],
            "devops": ["docker", "kubernetes", "ci/cd", "deployment"],
            "languages": ["python", "java", "go", "rust", "c++", "typescript"]
        }

        for category, keywords in categories.items():
            if any(kw in topic_lower for kw in keywords):
                return category

        return "other"

    def get_interview_calendar(self, user_id: str, months: int = 6) -> Dict:
        """
        Get interview frequency data for calendar heatmap.

        GitHub-style contribution graph showing practice consistency.
        """
        if not self.graph or not self.graph.driver:
            return {"error": "Cognitive graph not available"}

        try:
            cypher = """
            MATCH (i:Interview {user_id: $user_id})
            RETURN i.timestamp as date, count(i) as count
            ORDER BY i.timestamp
            """

            with self.graph.driver.session() as session:
                result = session.run(cypher, user_id=user_id)
                interviews = [dict(r) for r in result]

            # Group by date
            daily_counts = defaultdict(int)
            for interview in interviews:
                if interview.get("date"):
                    date_key = interview["date"].strftime("%Y-%m-%d") if hasattr(interview["date"], "strftime") else str(interview["date"])[:10]
                    daily_counts[date_key] += interview.get("count", 1)

            # Calculate streaks and stats
            sorted_dates = sorted(daily_counts.keys())
            current_streak = 0
            longest_streak = 0
            temp_streak = 0

            for i, date_str in enumerate(sorted_dates):
                if i == 0:
                    temp_streak = 1
                else:
                    # Check if consecutive
                    prev_date = datetime.strptime(sorted_dates[i-1], "%Y-%m-%d")
                    curr_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if (curr_date - prev_date).days == 1:
                        temp_streak += 1
                    else:
                        longest_streak = max(longest_streak, temp_streak)
                        temp_streak = 1

            longest_streak = max(longest_streak, temp_streak)

            # Current streak (from today backwards)
            today = datetime.now()
            for i in range(365):
                check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                if check_date in daily_counts:
                    current_streak += 1
                else:
                    break

            return {
                "user_id": user_id,
                "daily_activity": dict(daily_counts),
                "total_interviews": len(interviews),
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "most_active_day": max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None,
                "average_per_week": round(len(interviews) / (months * 4.33), 1) if months > 0 else 0
            }

        except Exception as e:
            logger.error("[Analytics] Interview calendar error: %s", str(e))
            return {"error": "An internal error occurred"}

    def get_performance_trends(self, user_id: str) -> Dict:
        """
        Get overall performance trends across all skills.

        Returns trending skills (improving, declining, stable).
        """
        if not self.graph or not self.graph.driver:
            return {"error": "Cognitive graph not available"}

        try:
            # Get all skills with progression
            cypher = """
            MATCH (i:Interview {user_id: $user_id})-[:CONTAINS]->(q:Question)
                  -[:ANSWERED_WITH]->(a:Answer)-[:DEMONSTRATES]->(s:Skill)
            RETURN s.name as skill,
                   count(*) as mentions,
                   avg(a.confidence) as avg_confidence,
                   collect(a.confidence) as confidences
            ORDER BY mentions DESC
            """

            with self.graph.driver.session() as session:
                result = session.run(cypher, user_id=user_id)
                skills_data = [dict(r) for r in result]

            # Categorize trends
            improving = []
            declining = []
            stable = []

            for skill_data in skills_data:
                confidences = skill_data.get("confidences", [])
                if len(confidences) >= 2:
                    # Compare first half vs second half
                    mid = len(confidences) // 2
                    first_avg = sum(confidences[:mid]) / max(mid, 1)
                    second_avg = sum(confidences[mid:]) / max(len(confidences) - mid, 1)
                    trend = second_avg - first_avg

                    skill_info = {
                        "name": skill_data["skill"],
                        "mentions": skill_data["mentions"],
                        "current_confidence": round(skill_data["avg_confidence"], 2),
                        "trend": round(trend, 2)
                    }

                    if trend > 0.1:
                        improving.append(skill_info)
                    elif trend < -0.1:
                        declining.append(skill_info)
                    else:
                        stable.append(skill_info)
                else:
                    stable.append({
                        "name": skill_data["skill"],
                        "mentions": skill_data["mentions"],
                        "current_confidence": round(skill_data["avg_confidence"], 2),
                        "trend": 0
                    })

            return {
                "improving": sorted(improving, key=lambda x: x["trend"], reverse=True)[:5],
                "declining": sorted(declining, key=lambda x: x["trend"])[:5],
                "stable": stable[:10],
                "total_skills": len(skills_data),
                "strongest_skill": max(skills_data, key=lambda x: x["avg_confidence"]) if skills_data else None,
                "most_practiced": max(skills_data, key=lambda x: x["mentions"]) if skills_data else None
            }

        except Exception as e:
            logger.error("[Analytics] Performance trends error: %s", str(e))
            return {"error": "An internal error occurred"}

    def get_dashboard_summary(self, user_id: str) -> Dict:
        """
        Get summary for analytics dashboard.

        Combines key metrics from all analytics.
        """
        trends = self.get_performance_trends(user_id)
        calendar = self.get_interview_calendar(user_id, months=3)

        # Get top skills
        top_skills = trends.get("improving", [])[:3] + trends.get("stable", [])[:2]

        return {
            "user_id": user_id,
            "summary": {
                "total_interviews": calendar.get("total_interviews", 0),
                "current_streak": calendar.get("current_streak", 0),
                "total_skills": trends.get("total_skills", 0),
                "improving_count": len(trends.get("improving", [])),
                "needs_attention_count": len(trends.get("declining", []))
            },
            "top_skills": top_skills,
            "recent_activity": calendar.get("daily_activity", {}),
            "recommendations": self._generate_recommendations(trends, calendar)
        }

    def _generate_recommendations(self, trends: Dict, calendar: Dict) -> List[str]:
        """Generate recommendations based on analytics"""
        recommendations = []

        if calendar.get("current_streak", 0) < 3:
            recommendations.append("Try to practice daily to build consistency")

        if len(trends.get("declining", [])) > 0:
            declining_names = [s["name"] for s in trends["declining"][:3]]
            recommendations.append(f"Review these skills: {', '.join(declining_names)}")

        if calendar.get("total_interviews", 0) < 10:
            recommendations.append("Consider doing more mock interviews to build experience")

        if not recommendations:
            recommendations.append("Great progress! Keep up the consistent practice")

        return recommendations


# Global instance
analytics = AnalyticsEngine()


# Convenience functions
def get_skill_progression(user_id: str, skill: str) -> Dict:
    """Get skill progression - convenience function"""
    return analytics.get_skill_progression(user_id, skill)


def get_dashboard_data(user_id: str) -> Dict:
    """Get dashboard summary - convenience function"""
    return analytics.get_dashboard_summary(user_id)

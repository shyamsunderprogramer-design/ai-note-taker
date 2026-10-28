/**
 * AnalyticsScreen — show usage stats (conversations recorded,
 * total duration, top topics, etc.) fetched from the backend.
 */
import React, { useState, useEffect } from "react"
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from "react-native"
import apiService from "../services/api"

export default function AnalyticsScreen() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const load = async () => {
    try {
      const data = await apiService.getAnalytics()
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const onRefresh = () => {
    setRefreshing(true)
    load()
  }

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#3b82f6" size="large" />
      </View>
    )
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.error}>{error}</Text>
      </View>
    )
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <Text style={styles.title}>Your Analytics</Text>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Interviews</Text>
        <Text style={styles.cardValue}>{stats?.summary?.total_interviews ?? 0}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Current Streak</Text>
        <Text style={styles.cardValue}>
          {stats?.summary?.current_streak ?? 0} days
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Skills Tracked</Text>
        <Text style={styles.cardValue}>{stats?.summary?.total_skills ?? 0}</Text>
      </View>

      {stats?.topTopics && stats.topTopics.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardLabel}>Top Topics</Text>
          {stats.topTopics.map((t, i) => (
            <Text key={i} style={styles.topicItem}>
              • {t.name} ({t.count})
            </Text>
          ))}
        </View>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a", padding: 16 },
  centered: {
    flex: 1,
    backgroundColor: "#0f172a",
    justifyContent: "center",
    alignItems: "center",
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#fff",
    marginBottom: 16,
  },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  cardLabel: {
    color: "#94a3b8",
    fontSize: 12,
    textTransform: "uppercase",
    marginBottom: 4,
  },
  cardValue: {
    color: "#fff",
    fontSize: 28,
    fontWeight: "700",
  },
  topicItem: {
    color: "#e2e8f0",
    fontSize: 14,
    marginTop: 4,
  },
  error: { color: "#f87171" },
})

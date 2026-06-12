// 01-create-indexes.cypher
// Creates performance indexes for the ANT cognitive graph.
// Run automatically by the Neo4j container on first start
// (mounted at /var/lib/neo4j/import/).
//
// Idempotent: IF NOT EXISTS is used for all CREATE INDEX statements
// so re-running this script is safe.

CREATE INDEX conversation_id_index IF NOT EXISTS
FOR (c:Conversation) ON (c.id);

CREATE INDEX entity_name_index IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX topic_name_index IF NOT EXISTS
FOR (t:Topic) ON (t.name);

CREATE INDEX speaker_name_index IF NOT EXISTS
FOR (s:Speaker) ON (s.name);

CREATE INDEX insight_id_index IF NOT EXISTS
FOR (i:Insight) ON (i.id);

// Composite indexes for common query patterns
CREATE INDEX conversation_date_index IF NOT EXISTS
FOR (c:Conversation) ON (c.started_at);

CREATE INDEX entity_type_name_index IF NOT EXISTS
FOR (e:Entity) ON (e.type, e.name);

// Full-text search indexes for transcript search
CREATE FULLTEXT INDEX transcript_text_index IF NOT EXISTS
FOR (c:Conversation) ON EACH [c.title, c.summary];

CREATE FULLTEXT INDEX insight_text_index IF NOT EXISTS
FOR (i:Insight) ON EACH [i.title, i.body];

// Constraints to prevent duplicate core records
CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS
FOR (c:Conversation) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT insight_id_unique IF NOT EXISTS
FOR (i:Insight) REQUIRE i.id IS UNIQUE;

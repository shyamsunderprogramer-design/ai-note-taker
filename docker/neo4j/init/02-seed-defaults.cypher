// 02-seed-defaults.cypher
// Seeds the cognitive graph with default entity types and topic
// categories. Only runs on a fresh database (MERGE is used so
// re-running is safe and idempotent).
//
// This is OPTIONAL — comment out the import or remove this file
// to skip seeding.

MERGE (et:EntityType {name: 'Person'})
  ON CREATE SET et.description = 'Individuals mentioned in conversations',
                et.icon = '👤';

MERGE (et:EntityType {name: 'Organization'})
  ON CREATE SET et.description = 'Companies, teams, and institutions',
                et.icon = '🏢';

MERGE (et:EntityType {name: 'Place'})
  ON CREATE SET et.description = 'Geographic locations and venues',
                et.icon = '📍';

MERGE (et:EntityType {name: 'Concept'})
  ON CREATE SET et.description = 'Abstract ideas and topics',
                et.icon = '💡';

MERGE (et:EntityType {name: 'Event'})
  ON CREATE SET et.description = 'Meetings, deadlines, and milestones',
                et.icon = '📅';

MERGE (et:EntityType {name: 'Technology'})
  ON CREATE SET et.description = 'Software, hardware, and tools',
                et.icon = '⚙️';

MERGE (et:EntityType {name: 'Document'})
  ON CREATE SET et.description = 'Reports, articles, and references',
                et.icon = '📄';

// Default topic categories
MERGE (tc:TopicCategory {name: 'Work'})
  ON CREATE SET tc.color = '#3b82f6';

MERGE (tc:TopicCategory {name: 'Personal'})
  ON CREATE SET tc.color = '#10b981';

MERGE (tc:TopicCategory {name: 'Learning'})
  ON CREATE SET tc.color = '#f59e0b';

MERGE (tc:TopicCategory {name: 'Health'})
  ON CREATE SET tc.color = '#ef4444';

MERGE (tc:TopicCategory {name: 'Finance'})
  ON CREATE SET tc.color = '#8b5cf6';

MERGE (tc:TopicCategory {name: 'Other'})
  ON CREATE SET tc.color = '#6b7280';

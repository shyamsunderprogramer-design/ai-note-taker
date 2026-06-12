/**
 * JobTrackerScreen — list of job applications tracked by the user.
 * Backed by the /jobs endpoints on the backend.
 */
import React, { useState, useEffect } from "react"
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
} from "react-native"
import apiService from "../services/api"

const STATUS_COLORS = {
  saved: "#64748b",
  applied: "#3b82f6",
  interviewing: "#f59e0b",
  offer: "#10b981",
  rejected: "#ef4444",
}

export default function JobTrackerScreen() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const load = async () => {
    try {
      const data = await apiService.listJobs()
      setJobs(data)
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
    <FlatList
      style={styles.container}
      data={jobs}
      keyExtractor={(item) => String(item.id)}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true)
            load()
          }}
        />
      }
      ListEmptyComponent={
        <Text style={styles.empty}>No jobs tracked yet.</Text>
      }
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.title}>{item.title}</Text>
            <View
              style={[
                styles.badge,
                { backgroundColor: STATUS_COLORS[item.status] || "#64748b" },
              ]}
            >
              <Text style={styles.badgeText}>{item.status}</Text>
            </View>
          </View>
          <Text style={styles.company}>{item.company}</Text>
          {item.location && (
            <Text style={styles.meta}>📍 {item.location}</Text>
          )}
          {item.applied_at && (
            <Text style={styles.meta}>
              Applied {new Date(item.applied_at).toLocaleDateString()}
            </Text>
          )}
        </View>
      )}
    />
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
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  title: { color: "#fff", fontSize: 16, fontWeight: "600", flex: 1 },
  company: { color: "#cbd5e1", fontSize: 14, marginBottom: 4 },
  meta: { color: "#64748b", fontSize: 12, marginTop: 2 },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  empty: { color: "#64748b", textAlign: "center", marginTop: 32 },
  error: { color: "#f87171" },
})

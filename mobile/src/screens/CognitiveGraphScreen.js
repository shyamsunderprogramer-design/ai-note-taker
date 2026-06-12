/**
 * CognitiveGraphScreen — read-only view of the user's knowledge
 * graph (entities, topics, conversations). Uses a WebView to
 * render the existing web cognitive-graph.html since building
 * a native graph renderer is out of scope.
 */
import React, { useState, useEffect } from "react"
import { View, Text, StyleSheet, ActivityIndicator } from "react-native"
import { WebView } from "react-native-webview"
import { useSettingsStore } from "../store/settings"

export default function CognitiveGraphScreen() {
  const apiUrl = useSettingsStore((s) => s.apiUrl)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.error}>Failed to load graph: {error}</Text>
      </View>
    )
  }

  return (
    <View style={styles.container}>
      {loading && (
        <View style={styles.loading}>
          <ActivityIndicator color="#3b82f6" size="large" />
        </View>
      )}
      <WebView
        source={{ uri: `${apiUrl}/static/cognitive-graph.html` }}
        style={styles.webview}
        onLoadEnd={() => setLoading(false)}
        onError={(e) => setError(e.nativeEvent.description)}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  webview: { flex: 1 },
  loading: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#0f172a",
  },
  error: { color: "#f87171", padding: 16, textAlign: "center" },
})

/**
 * ANT Mobile — Main App component with navigation.
 */
import React, { useState, useEffect } from "react"
import { NavigationContainer } from "@react-navigation/native"
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs"
import { createStackNavigator } from "@react-navigation/stack"
import { View, Text, StyleSheet, ActivityIndicator } from "react-native"

import apiService from "./services/api"

// ── Screens ──────────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleLogin = async () => {
    setLoading(true)
    setError("")
    try {
      await apiService.login(username, password)
      onLogin()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={styles.centered}>
      <Text style={styles.title}>AI Note Taker</Text>
      <Text style={styles.subtitle}>Sign in to continue</Text>
      {/* Login form would go here — TextInput components */}
      <Text onPress={handleLogin} style={styles.button}>
        {loading ? "Signing in..." : "Sign In"}
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  )
}

function ConversationsScreen() {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiService.getConversations().then(data => {
      setConversations(data.conversations || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" /></View>
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Conversations</Text>
      {conversations.length === 0 ? (
        <Text style={styles.empty}>No conversations yet</Text>
      ) : (
        conversations.map(conv => (
          <View key={conv.id} style={styles.card}>
            <Text style={styles.cardTitle}>{conv.title || "Untitled"}</Text>
            <Text style={styles.cardSub}>{conv.message_count || 0} messages</Text>
          </View>
        ))
      )}
    </View>
  )
}

function InterviewScreen() {
  return (
    <View style={styles.centered}>
      <Text style={styles.header}>Interview Coach</Text>
      <Text style={styles.empty}>Start a practice session</Text>
    </View>
  )
}

function CareerScreen() {
  return (
    <View style={styles.centered}>
      <Text style={styles.header}>Career Tools</Text>
      <Text style={styles.empty}>Cover letters, resume, salary</Text>
    </View>
  )
}

function SettingsScreen({ onLogout }) {
  return (
    <View style={styles.centered}>
      <Text style={styles.header}>Settings</Text>
      <Text onPress={onLogout} style={styles.button}>Sign Out</Text>
    </View>
  )
}

// ── Navigation ──────────────────────────────────────────────────────────────

const Tab = createBottomTabNavigator()
const Stack = createStackNavigator()

function MainTabs({ onLogout }) {
  return (
    <Tab.Navigator>
      <Tab.Screen name="Conversations" component={ConversationsScreen} />
      <Tab.Screen name="Interview" component={InterviewScreen} />
      <Tab.Screen name="Career" component={CareerScreen} />
      <Tab.Screen name="Settings">
        {() => <SettingsScreen onLogout={onLogout} />}
      </Tab.Screen>
    </Tab.Navigator>
  )
}

// ── App Root ─────────────────────────────────────────────────────────────────

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    apiService.init().then(() => {
      if (apiService.token) {
        setIsLoggedIn(true)
      }
      setChecking(false)
    })
  }, [])

  if (checking) {
    return <View style={styles.centered}><ActivityIndicator size="large" /></View>
  }

  return (
    <NavigationContainer>
      {isLoggedIn ? (
        <MainTabs onLogout={() => {
          apiService.logout()
          setIsLoggedIn(false)
        }} />
      ) : (
        <Stack.Navigator>
          <Stack.Screen name="Login" options={{ headerShown: false }}>
            {() => <LoginScreen onLogin={() => setIsLoggedIn(true)} />}
          </Stack.Screen>
        </Stack.Navigator>
      )}
    </NavigationContainer>
  )
}

// ── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f0f0f", padding: 16 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f0f0f" },
  title: { fontSize: 28, fontWeight: "bold", color: "#fff", marginBottom: 8 },
  subtitle: { fontSize: 16, color: "#aaa", marginBottom: 24 },
  header: { fontSize: 22, fontWeight: "bold", color: "#fff", marginBottom: 16 },
  empty: { fontSize: 14, color: "#888", textAlign: "center", marginTop: 40 },
  button: { fontSize: 16, color: "#4f8ef7", marginTop: 16, padding: 12 },
  card: { backgroundColor: "#1a1a2e", borderRadius: 12, padding: 16, marginBottom: 12 },
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#fff" },
  cardSub: { fontSize: 13, color: "#888", marginTop: 4 },
  error: { fontSize: 14, color: "#ff4444", marginTop: 8 },
})
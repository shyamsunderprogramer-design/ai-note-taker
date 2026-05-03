/**
 * ANT Mobile — Main App component with navigation.
 * T21: Mobile App (React Native)
 */
import React, { useState, useEffect } from "react"
import { NavigationContainer } from "@react-navigation/native"
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs"
import { createStackNavigator } from "@react-navigation/stack"
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, TextInput, TouchableOpacity } from "react-native"

import apiService from "./services/api"
import notificationService from "./services/notifications"

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
      <TextInput
        style={styles.input}
        placeholder="Username"
        placeholderTextColor="#888"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#888"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      <TouchableOpacity onPress={handleLogin} style={styles.buttonPrimary}>
        <Text style={styles.buttonText}>
          {loading ? "Signing in..." : "Sign In"}
        </Text>
      </TouchableOpacity>
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
    <ScrollView style={styles.container}>
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
    </ScrollView>
  )
}

function InterviewScreen() {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)

  useEffect(() => {
    apiService.getInterviewQuestions("behavioral", 10).then(data => {
      setQuestions(data.questions || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" /></View>
  }

  const current = questions[currentIndex]

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Interview Coach</Text>
      {current ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Question {currentIndex + 1} of {questions.length}</Text>
          <Text style={styles.questionText}>{current.question}</Text>
          <TouchableOpacity onPress={() => setShowAnswer(!showAnswer)} style={styles.buttonPrimary}>
            <Text style={styles.buttonText}>{showAnswer ? "Hide Answer" : "Show Answer"}</Text>
          </TouchableOpacity>
          {showAnswer && current.expected_answer ? (
            <View style={styles.answerBox}>
              {current.expected_answer.key_points?.map((pt, i) => (
                <Text key={i} style={styles.answerPoint}>• {pt}</Text>
              ))}
            </View>
          ) : null}
          <View style={styles.navRow}>
            <TouchableOpacity
              disabled={currentIndex === 0}
              onPress={() => { setCurrentIndex(currentIndex - 1); setShowAnswer(false) }}
              style={[styles.buttonSecondary, currentIndex === 0 && styles.disabled]}
            >
              <Text style={styles.buttonSecondaryText}>Previous</Text>
            </TouchableOpacity>
            <TouchableOpacity
              disabled={currentIndex >= questions.length - 1}
              onPress={() => { setCurrentIndex(currentIndex + 1); setShowAnswer(false) }}
              style={[styles.buttonSecondary, currentIndex >= questions.length - 1 && styles.disabled]}
            >
              <Text style={styles.buttonSecondaryText}>Next</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <Text style={styles.empty}>No questions available</Text>
      )}
    </ScrollView>
  )
}

function CareerScreen() {
  const [company, setCompany] = useState("")
  const [prep, setPrep] = useState(null)
  const [loading, setLoading] = useState(false)

  const fetchPrep = async () => {
    if (!company.trim()) return
    setLoading(true)
    try {
      const data = await apiService.getInterviewPrep(company.trim())
      setPrep(data)
    } catch (e) {
      setPrep({ error: "Failed to load prep" })
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Career Tools</Text>
      <TextInput
        style={styles.input}
        placeholder="Company name (e.g., Google)"
        placeholderTextColor="#888"
        value={company}
        onChangeText={setCompany}
      />
      <TouchableOpacity onPress={fetchPrep} style={styles.buttonPrimary}>
        <Text style={styles.buttonText}>{loading ? "Loading..." : "Get Interview Prep"}</Text>
      </TouchableOpacity>
      {prep && !prep.error ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Prep for {company}</Text>
          <Text style={styles.cardSub}>{JSON.stringify(prep, null, 2).slice(0, 400)}</Text>
        </View>
      ) : prep?.error ? (
        <Text style={styles.error}>{prep.error}</Text>
      ) : null}
    </ScrollView>
  )
}

function SettingsScreen({ onLogout }) {
  const [apiUrl, setApiUrl] = useState("")

  useEffect(() => {
    apiService.init().then(() => setApiUrl(apiService.baseUrl))
  }, [])

  return (
    <View style={styles.centered}>
      <Text style={styles.header}>Settings</Text>
      <TextInput
        style={styles.input}
        placeholder="API URL"
        placeholderTextColor="#888"
        value={apiUrl}
        onChangeText={setApiUrl}
        onBlur={() => apiService.setApiUrl(apiUrl)}
      />
      <TouchableOpacity onPress={onLogout} style={styles.buttonPrimary}>
        <Text style={styles.buttonText}>Sign Out</Text>
      </TouchableOpacity>
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
    notificationService.requestPermissions()
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
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f0f0f", padding: 16 },
  title: { fontSize: 28, fontWeight: "bold", color: "#fff", marginBottom: 8 },
  subtitle: { fontSize: 16, color: "#aaa", marginBottom: 24 },
  header: { fontSize: 22, fontWeight: "bold", color: "#fff", marginBottom: 16 },
  empty: { fontSize: 14, color: "#888", textAlign: "center", marginTop: 40 },
  input: { width: "100%", backgroundColor: "#1a1a2e", color: "#fff", borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 15 },
  buttonPrimary: { backgroundColor: "#4f8ef7", borderRadius: 8, paddingVertical: 12, paddingHorizontal: 24, alignItems: "center", marginTop: 8 },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  buttonSecondary: { backgroundColor: "#2a2a3e", borderRadius: 8, paddingVertical: 10, paddingHorizontal: 20, alignItems: "center", flex: 1, marginHorizontal: 4 },
  buttonSecondaryText: { color: "#ccc", fontSize: 14 },
  disabled: { opacity: 0.4 },
  card: { backgroundColor: "#1a1a2e", borderRadius: 12, padding: 16, marginBottom: 12 },
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#fff" },
  cardSub: { fontSize: 13, color: "#888", marginTop: 4 },
  questionText: { fontSize: 16, color: "#eee", marginVertical: 12, lineHeight: 22 },
  answerBox: { backgroundColor: "#252540", borderRadius: 8, padding: 12, marginTop: 12 },
  answerPoint: { fontSize: 14, color: "#ccc", marginVertical: 4 },
  navRow: { flexDirection: "row", marginTop: 16 },
  error: { fontSize: 14, color: "#ff4444", marginTop: 8 },
})

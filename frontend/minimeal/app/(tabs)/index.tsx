import { useEffect, useState } from 'react';
import { Pressable, StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { API_BASE_URL } from '@/constants/api';

type HealthResponse = {
  status: string;
};

export default function HomeScreen() {
  const [healthStatus, setHealthStatus] = useState('Checking backend...');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function checkBackend() {
    setErrorMessage(null);
    setHealthStatus('Checking backend...');

    try {
      const response = await fetch(`${API_BASE_URL}/`);

      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`);
      }

      const data: HealthResponse = await response.json();
      setHealthStatus(data.status);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      setHealthStatus('Backend unavailable');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Unknown error while contacting the backend.'
      );
    }
  }

  useEffect(() => {
    checkBackend();
  }, []);

  return (
    <ThemedView style={styles.screen}>
      <ThemedView style={styles.hero}>
        <ThemedText type="title" style={styles.title}>
          Minimeal
        </ThemedText>
        <ThemedText style={styles.subtitle}>
          Natural-language meal logging with lightweight nutrition guidance.
        </ThemedText>
      </ThemedView>

      <ThemedView style={styles.card} lightColor="#F7F9FC" darkColor="#1E242C">
        <ThemedText type="subtitle">Backend check</ThemedText>
        <ThemedText style={styles.label}>API base URL</ThemedText>
        <ThemedText type="defaultSemiBold">{API_BASE_URL}</ThemedText>

        <ThemedView style={styles.statusRow} lightColor="#F7F9FC" darkColor="#1E242C">
          <ThemedText style={styles.label}>Status</ThemedText>
          <ThemedText type="defaultSemiBold">{healthStatus}</ThemedText>
        </ThemedView>

        {lastUpdated ? (
          <ThemedText style={styles.meta}>Last checked at {lastUpdated}</ThemedText>
        ) : null}

        {errorMessage ? (
          <ThemedText style={styles.errorText}>
            Make sure the FastAPI server is running on port 8000. Error: {errorMessage}
          </ThemedText>
        ) : null}

        <Pressable style={styles.button} onPress={checkBackend}>
          <ThemedText style={styles.buttonText}>Check again</ThemedText>
        </Pressable>
      </ThemedView>

      <ThemedView style={styles.card} lightColor="#FFF6E8" darkColor="#2A2218">
        <ThemedText type="subtitle">Next step</ThemedText>
        <ThemedText>
          Once this status card is loading successfully on iOS, we can replace it with meal input
          and real API requests.
        </ThemedText>
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 72,
    gap: 18,
  },
  hero: {
    gap: 8,
  },
  title: {
    lineHeight: 38,
  },
  subtitle: {
    fontSize: 18,
    lineHeight: 26,
  },
  card: {
    borderRadius: 20,
    padding: 18,
    gap: 12,
  },
  label: {
    opacity: 0.7,
    fontSize: 14,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  statusRow: {
    gap: 6,
  },
  meta: {
    opacity: 0.7,
  },
  errorText: {
    color: '#B14A2B',
    lineHeight: 22,
  },
  button: {
    marginTop: 4,
    backgroundColor: '#0A7EA4',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
});

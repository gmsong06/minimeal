import { StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function TabTwoScreen() {
  return (
    <ThemedView style={styles.screen}>
      <ThemedText type="title">Build Notes</ThemedText>
      <ThemedView style={styles.card} lightColor="#EEF8F6" darkColor="#182523">
        <ThemedText type="subtitle">What to focus on first</ThemedText>
        <ThemedText>1. Make the home screen load on iOS.</ThemedText>
        <ThemedText>2. Confirm the backend health check succeeds.</ThemedText>
        <ThemedText>3. Replace the status card with a meal input flow.</ThemedText>
      </ThemedView>
      <ThemedView style={styles.card} lightColor="#F7F9FC" darkColor="#1E242C">
        <ThemedText type="subtitle">Frontend scope for now</ThemedText>
        <ThemedText>
          Keep the first iteration simple: one input, one submit action, and one response area.
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
    gap: 8,
  },
  card: {
    marginTop: 10,
    borderRadius: 20,
    padding: 18,
    gap: 10,
  },
});

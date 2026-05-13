import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/context/auth-context';

export function AccountGate() {
  const { seededAccounts, isLoadingAccounts, authError, login, refreshAccounts } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  async function submitLogin(nextUsername: string, nextPassword: string) {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      await login(nextUsername.trim(), nextPassword.trim());
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Login failed.');
    } finally {
      setIsLoggingIn(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <ScrollView className="flex-1 bg-white" contentContainerClassName="px-6 pb-16 pt-8">
        <Text className="text-[38px] tracking-[-1px] text-ink">Minimeal</Text>
        <Text className="mt-3 text-[16px] text-muted">
          Sign in with a seeded demo account to sync meals to the cloud database.
        </Text>

        {authError ? (
          <View className="mt-5 rounded-[16px] bg-[#f7ece7] px-4 py-3">
            <Text className="text-[14px] text-[#a1583d]">{authError}</Text>
          </View>
        ) : null}

        {loginError ? (
          <View className="mt-4 rounded-[16px] bg-[#f7ece7] px-4 py-3">
            <Text className="text-[14px] text-[#a1583d]">{loginError}</Text>
          </View>
        ) : null}

        <View className="mt-6 gap-3">
          {isLoadingAccounts ? (
            <View className="flex-row items-center gap-3">
              <ActivityIndicator size="small" color="#8A847C" />
              <Text className="text-[15px] text-muted">Loading seeded accounts...</Text>
            </View>
          ) : (
            seededAccounts.map((account) => (
              <Pressable
                key={account.username}
                className="rounded-[20px] border border-line bg-card px-4 py-4"
                disabled={isLoggingIn}
                onPress={() => {
                  setUsername(account.username);
                  setPassword(account.password);
                  void submitLogin(account.username, account.password);
                }}>
                <Text className="text-[17px] text-ink">{account.display_name}</Text>
                <Text className="mt-1 text-[14px] text-muted">
                  {account.username} / {account.password}
                </Text>
              </Pressable>
            ))
          )}
        </View>

        <View className="mt-8 gap-3">
          <Text className="text-[14px] uppercase tracking-[1.6px] text-muted">
            Manual login
          </Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            className="rounded-[16px] border border-line px-4 py-3 text-[16px] text-ink"
            placeholder="Username"
            value={username}
            onChangeText={setUsername}
          />
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            className="rounded-[16px] border border-line px-4 py-3 text-[16px] text-ink"
            placeholder="Password"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />
          <Pressable
            className={`mt-1 rounded-full px-5 py-3 ${
              isLoggingIn ? 'bg-[#d9d4cc]' : 'bg-ink'
            }`}
            disabled={isLoggingIn}
            onPress={() => {
              void submitLogin(username, password);
            }}>
            <Text className="text-center text-[16px] font-medium text-white">
              {isLoggingIn ? 'Signing in...' : 'Sign in'}
            </Text>
          </Pressable>
          <Pressable
            className="self-start rounded-full border border-line bg-white px-4 py-2"
            disabled={isLoadingAccounts || isLoggingIn}
            onPress={() => {
              void refreshAccounts();
            }}>
            <Text className="text-[14px] text-ink">Refresh accounts</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

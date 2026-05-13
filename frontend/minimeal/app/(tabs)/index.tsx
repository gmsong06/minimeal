import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { useIsFocused } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { AccountGate } from '@/components/auth/account-gate';
import { API_BASE_URL } from '@/constants/api';
import { useAuth } from '@/context/auth-context';

type HealthResponse = {
  status: string;
};

type DailySummaryItem = {
  nutrient_id: number;
  name: string;
  percent_dv_so_far: number;
  status: string;
};

type DailySummaryResponse = {
  date: string;
  timezone: string;
  nutrient_totals: Record<string, number>;
  formatted_summary: DailySummaryItem[];
};

type MealLogEntry = {
  meal_id: string;
  time_stamp: string;
  meal_description?: string | null;
};

type NutrientProgressState = 'done' | 'progress' | 'empty';

function getVitaminBadgeLabel(name: string) {
  const normalized = name.trim().toLowerCase();
  const vitaminMap: Record<string, string> = {
    'thiamin': 'B1',
    'riboflavin': 'B2',
    'niacin': 'B3',
    'choline': 'B4',
    'pantothenic acid': 'B5',
    'vitamin b6': 'B6',
    'biotin': 'B7',
    'folate': 'B9',
    'vitamin b12': 'B12',
  };

  const directMatch = vitaminMap[normalized];
  if (directMatch) {
    return directMatch;
  }

  const vitaminMatch = normalized.match(/vitamin\s+([a-z0-9]+)/i);
  if (vitaminMatch) {
    return vitaminMatch[1].toUpperCase();
  }

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

function getProgressState(item: DailySummaryItem): NutrientProgressState {
  const normalizedStatus = item.status.trim().toLowerCase();

  if (
    item.percent_dv_so_far >= 100 ||
    normalizedStatus.includes('met') ||
    normalizedStatus.includes('adequate') ||
    normalizedStatus.includes('complete')
  ) {
    return 'done';
  }

  if (item.percent_dv_so_far > 0) {
    return 'progress';
  }

  return 'empty';
}

function getProgressCopy(state: NutrientProgressState) {
  if (state === 'done') {
    return {
      label: 'Covered',
      detail: 'Check',
      icon: 'checkmark',
      iconColor: '#3a7d44',
      badgeClassName: 'bg-[#e6f3e8]',
    } as const;
  }

  if (state === 'progress') {
    return {
      label: 'In progress',
      detail: 'Building',
      icon: 'time-outline',
      iconColor: '#9b6b2f',
      badgeClassName: 'bg-[#f6ead8]',
    } as const;
  }

  return {
    label: 'Not exposed',
    detail: 'None yet',
    icon: 'remove',
    iconColor: '#8f8a83',
    badgeClassName: 'bg-[#ece8e1]',
  } as const;
}

export default function HomeScreen() {
  const isFocused = useIsFocused();
  const { session, authHeaders, logout } = useAuth();
  const [healthStatus, setHealthStatus] = useState('Checking backend...');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dailySummary, setDailySummary] = useState<DailySummaryItem[]>([]);
  const [recentMeals, setRecentMeals] = useState<MealLogEntry[]>([]);
  const micronutrientCards = useMemo(
    () =>
      dailySummary.slice(0, 8).map((item) => {
        const state = getProgressState(item);
        return {
          ...item,
          badgeLabel: getVitaminBadgeLabel(item.name),
          progress: getProgressCopy(state),
          state,
        };
      }),
    [dailySummary]
  );

  const refreshHome = useCallback(async () => {
    setErrorMessage(null);
    setHealthStatus('Checking backend...');

    try {
      const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const [healthResponse, summaryResponse, mealsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/`, { headers: authHeaders }),
        fetch(`${API_BASE_URL}/summary/today?tz_name=${encodeURIComponent(tzName)}`, {
          headers: authHeaders,
        }),
        fetch(`${API_BASE_URL}/meals`, { headers: authHeaders }),
      ]);

      if (!healthResponse.ok || !summaryResponse.ok || !mealsResponse.ok) {
        throw new Error('One or more home requests failed.');
      }

      const healthData: HealthResponse = await healthResponse.json();
      const summaryData: DailySummaryResponse = await summaryResponse.json();
      const mealsData: MealLogEntry[] = await mealsResponse.json();

      setHealthStatus(healthData.status);
      setDailySummary(summaryData.formatted_summary.slice(0, 4));
      setRecentMeals(mealsData.slice(-3).reverse());
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      setHealthStatus('Backend unavailable');
      setDailySummary([]);
      setRecentMeals([]);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Unknown error while contacting the backend.'
      );
    }
  }, [authHeaders]);

  useEffect(() => {
    if (isFocused && session) {
      refreshHome();
    }
  }, [isFocused, refreshHome, session]);

  if (!session) {
    return <AccountGate />;
  }

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <ScrollView className="flex-1 bg-white" contentContainerClassName="px-6 pb-32 pt-3">
        <View className="mb-10 gap-4">
          <Text className="text-[42px] font-medium tracking-[-1.2px] text-ink">Home</Text>
          <View className="flex-row items-center justify-between">
            <Text className="text-[14px] text-muted">Signed in as {session.display_name}</Text>
            <Pressable
              className="rounded-full border border-line bg-white px-4 py-2"
              onPress={logout}>
              <Text className="text-[13px] text-ink">Sign out</Text>
            </Pressable>
          </View>
        </View>

        <View className="mb-6 rounded-card border border-line bg-card px-5 py-5 shadow-float">
          <View className="mb-5 flex-row items-start justify-between">
            <View className="flex-1 pr-4">
              <Text className="mb-1 text-[14px] uppercase tracking-[2px] text-muted">
                System status
              </Text>
              <Text className="text-[28px] tracking-[-0.6px] text-ink">{healthStatus}</Text>
            </View>
            <View className="rounded-full bg-accentSoft px-3 py-2">
              <Text className="text-[13px] font-medium text-ink">
                {errorMessage ? 'Retrying' : 'Connected'}
              </Text>
            </View>
          </View>

          <View className="gap-4">
            <View className="rounded-[22px] bg-[#f3f1ec] px-4 py-4">
              <Text className="mb-1 text-[13px] uppercase tracking-[1.8px] text-muted">API</Text>
              <Text className="text-[16px] leading-6 text-ink">{API_BASE_URL}</Text>
            </View>

            {lastUpdated ? (
              <Text className="text-[15px] text-muted">Last checked at {lastUpdated}</Text>
            ) : null}

          </View>

          <Pressable
            className="mt-6 self-start rounded-full border border-line bg-white px-5 py-3"
            onPress={refreshHome}>
            <Text className="text-[16px] font-medium text-ink">Refresh</Text>
          </Pressable>
        </View>

        <View className="mb-6 rounded-card border border-line bg-card px-5 py-5">
          <Text className="mb-2 text-[14px] uppercase tracking-[2px] text-muted">
            Daily summary
          </Text>

          {micronutrientCards.length > 0 ? (
            <View className="flex-row flex-wrap gap-3">
              {micronutrientCards.map((item) => (
                <View
                  key={item.nutrient_id}
                  className="w-[47%] rounded-[22px] border border-line bg-white px-4 py-4">
                  <View className="mb-4 flex-row items-center justify-between">
                    <View className="h-11 w-11 items-center justify-center rounded-full bg-[#f3ede6]">
                      <Text className="text-[14px] font-semibold tracking-[0.3px] text-ink">
                        {item.badgeLabel}
                      </Text>
                    </View>
                    <View className={`rounded-full px-2.5 py-1 ${item.progress.badgeClassName}`}>
                      <Ionicons
                        name={item.progress.icon}
                        size={14}
                        color={item.progress.iconColor}
                      />
                    </View>
                  </View>

                  <Text className="mb-1 text-[18px] tracking-[-0.3px] text-ink">{item.name}</Text>
                  <Text className="mb-3 text-[14px] text-muted">
                    {item.percent_dv_so_far.toFixed(0)}% of daily value
                  </Text>

                  <Text className="text-[14px] font-medium text-ink">{item.progress.label}</Text>
                  <Text className="text-[13px] text-muted">{item.progress.detail}</Text>
                </View>
              ))}
            </View>
          ) : (
            <Text className="text-[16px] leading-7 text-muted">
              Log a meal to start building today&apos;s micronutrient snapshot.
            </Text>
          )}
        </View>

        <View className="flex-row gap-4">
          <View className="flex-1 rounded-card border border-line bg-warm px-5 py-5">
            <Text className="mb-2 text-[14px] uppercase tracking-[1.8px] text-muted">
              Recent meals
            </Text>
            {recentMeals.length > 0 ? (
              recentMeals.map((meal) => (
                <View key={meal.meal_id} className="mb-3 last:mb-0">
                  <Text className="text-[20px] leading-7 tracking-[-0.4px] text-ink">
                    {meal.meal_description || 'Meal log'}
                  </Text>
                  <Text className="text-[14px] text-muted">
                    {new Date(meal.time_stamp).toLocaleTimeString([], {
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </Text>
                </View>
              ))
            ) : (
              <Text className="text-[18px] leading-7 text-ink">
                Your latest meals will show up here after you log them.
              </Text>
            )}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

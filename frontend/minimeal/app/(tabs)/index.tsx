import { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { useIsFocused } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { API_BASE_URL } from '@/constants/api';

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

export default function HomeScreen() {
  const isFocused = useIsFocused();
  const [healthStatus, setHealthStatus] = useState('Checking backend...');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dailySummary, setDailySummary] = useState<DailySummaryItem[]>([]);
  const [recentMeals, setRecentMeals] = useState<MealLogEntry[]>([]);

  async function refreshHome() {
    setErrorMessage(null);
    setHealthStatus('Checking backend...');

    try {
      const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const [healthResponse, summaryResponse, mealsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/`),
        fetch(`${API_BASE_URL}/summary/today?tz_name=${encodeURIComponent(tzName)}`),
        fetch(`${API_BASE_URL}/meals`),
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
  }

  useEffect(() => {
    if (isFocused) {
      refreshHome();
    }
  }, [isFocused]);

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <ScrollView className="flex-1 bg-white" contentContainerClassName="px-6 pb-32 pt-3">
        <View className="mb-10 gap-4">
          <Text className="text-[42px] font-medium tracking-[-1.2px] text-ink">Home</Text>
          <Text className="max-w-[300px] text-[18px] leading-7 text-muted">
            Daily summaries, soft signals, and a quick view of how your eating rhythm is going today.
          </Text>
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

            {errorMessage ? (
              <Text className="text-[15px] leading-6 text-[#b26545]">
                FastAPI didn&apos;t answer cleanly: {errorMessage}
              </Text>
            ) : (
              <Text className="text-[15px] leading-6 text-muted">
                Home now pulls your backend health, today&apos;s summary, and your latest meals.
              </Text>
            )}
          </View>

          <Pressable
            className="mt-6 self-start rounded-full border border-line bg-white px-5 py-3"
            onPress={refreshHome}>
            <Text className="text-[16px] font-medium text-ink">Refresh</Text>
          </Pressable>
        </View>

        <View className="mb-6 rounded-card border border-line bg-card px-5 py-5">
          <Text className="mb-5 text-[14px] uppercase tracking-[2px] text-muted">Daily summary</Text>

          {dailySummary.length > 0 ? (
            dailySummary.map((item) => (
              <View key={item.nutrient_id} className="border-b border-line py-4 last:border-b-0">
                <Text className="mb-1 text-[24px] tracking-[-0.4px] text-ink">{item.name}</Text>
                <Text className="mb-2 text-[16px] leading-6 text-muted">
                  {item.percent_dv_so_far.toFixed(1)}% of daily value so far
                </Text>
                <Text className="text-[15px] capitalize text-[#8f8a83]">{item.status}</Text>
              </View>
            ))
          ) : (
            <Text className="text-[16px] leading-7 text-muted">
              Log a meal to start building today&apos;s summary.
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
          <View className="w-[108px] rounded-card border border-line bg-accentSoft px-4 py-5">
            <Text className="mb-2 text-[14px] uppercase tracking-[1.8px] text-muted">Meals</Text>
            <Text className="text-[34px] tracking-[-0.8px] text-ink">{recentMeals.length}</Text>
            <Text className="text-[15px] text-muted">recent</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

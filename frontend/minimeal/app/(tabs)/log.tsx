import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as Haptics from 'expo-haptics';
import {
  ActivityIndicator,
  Animated,
  PanResponder,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useIsFocused } from '@react-navigation/native';

import { API_BASE_URL } from '@/constants/api';

const REVEAL_HEIGHT = 50;
const OPEN_THRESHOLD = 40;

type MealLogEntry = {
  meal_id: string;
  time_stamp: string;
  meal_description?: string | null;
  nutrient_exposure: Record<string, number>;
};

type MealCreateResponse = {
  processed_meal: {
    meal_description?: string | null;
  };
  nutrient_exposure: Record<string, number>;
  log_entry: MealLogEntry;
};

export default function LogScreen() {
  const isFocused = useIsFocused();
  const pullY = useRef(new Animated.Value(0)).current;
  const inputRef = useRef<TextInput>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [mealText, setMealText] = useState('');
  const [meals, setMeals] = useState<MealLogEntry[]>([]);
  const [isLoadingMeals, setIsLoadingMeals] = useState(false);
  const [isSavingMeal, setIsSavingMeal] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    console.log('LogScreen mounted');
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const id = setTimeout(() => {
      inputRef.current?.focus();
    }, 120);

    return () => clearTimeout(id);
  }, [isOpen]);

  const fetchMeals = useCallback(async () => {
    setIsLoadingMeals(true);
    setErrorMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/meals`);

      if (!response.ok) {
        throw new Error(`Failed to load meals (${response.status})`);
      }

      const data: MealLogEntry[] = await response.json();
      setMeals(data.slice().reverse());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load meals.');
    } finally {
      setIsLoadingMeals(false);
    }
  }, []);

  useEffect(() => {
    if (isFocused) {
      fetchMeals();
    }
  }, [fetchMeals, isFocused]);

  function clampPull(distance: number) {
    return Math.max(0, Math.min(REVEAL_HEIGHT, distance));
  }

  const animateOpen = useCallback(() => {
    Animated.spring(pullY, {
      toValue: REVEAL_HEIGHT,
      useNativeDriver: false,
      tension: 90,
      friction: 12,
      overshootClamping: true,
    }).start();
  }, [pullY]);

  const animateClosed = useCallback((onComplete?: () => void) => {
    Animated.timing(pullY, {
      toValue: 0,
      duration: 140,
      useNativeDriver: false,
    }).start(() => {
      onComplete?.();
    });
  }, [pullY]);

  const openInput = useCallback(() => {
    console.log('log input opened');
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    setIsOpen(true);
    setIsClosing(false);
    animateOpen();
  }, [animateOpen]);

  const closeInput = useCallback(() => {
    console.log('log input closed');
    setIsOpen(false);
    setIsClosing(true);
    animateClosed(() => {
      setIsClosing(false);
    });
  }, [animateClosed]);

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, gestureState) =>
          !isOpen && gestureState.dy > 8 && Math.abs(gestureState.dx) < 20,
        onPanResponderGrant: () => {
          console.log('log drag started');
        },
        onPanResponderMove: (_, gestureState) => {
          if (isOpen) {
            return;
          }

          const nextPull = clampPull(gestureState.dy);
          console.log('log pull move', {
            dy: gestureState.dy,
            pullDistance: nextPull,
          });
          pullY.setValue(nextPull);
        },
        onPanResponderRelease: (_, gestureState) => {
          const releasedPull = clampPull(gestureState.dy);
          console.log('log pull release', {
            dy: gestureState.dy,
            releasedPull,
            threshold: OPEN_THRESHOLD,
          });

          if (releasedPull >= OPEN_THRESHOLD) {
            openInput();
            return;
          }

          console.log('log input reset');
          animateClosed();
        },
        onPanResponderTerminate: () => {
          console.log('log gesture terminated');
          if (!isOpen) {
            animateClosed();
          }
        },
      }),
    [animateClosed, isOpen, openInput, pullY]
  );

  const saveMeal = useCallback(async () => {
    const trimmedMeal = mealText.trim();

    if (!trimmedMeal) {
      setErrorMessage('Type a meal before saving.');
      return;
    }

    setIsSavingMeal(true);
    setErrorMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/meals`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_meal: trimmedMeal,
          tz_name: Intl.DateTimeFormat().resolvedOptions().timeZone,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Failed to save meal (${response.status})`);
      }

      const data: MealCreateResponse = await response.json();
      console.log('meal create response', data);
      setMeals((current) => [data.log_entry, ...current]);
      setMealText('');
      closeInput();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to save meal.');
    } finally {
      setIsSavingMeal(false);
    }
  }, [closeInput, mealText]);

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <View
        className="flex-1 bg-white"
        {...(!isOpen && !isClosing ? panResponder.panHandlers : {})}>
        {isOpen ? (
          <Pressable className="absolute inset-0 z-10 bg-transparent" onPress={closeInput} />
        ) : null}

        <Animated.View
          className="overflow-hidden px-6"
          style={{
            height: pullY,
          }}>
          <View
            className="border-b border-line bg-white"
            style={{
              height: REVEAL_HEIGHT,
              justifyContent: 'flex-end',
              paddingBottom: 6,
            }}>
            <View className="flex-row items-center justify-between gap-3">
              <TextInput
                ref={inputRef}
                value={mealText}
                onChangeText={setMealText}
                placeholder="I ate..."
                placeholderTextColor="#b8b4ad"
                className="flex-1 text-[18px] leading-[22px] tracking-[0.1px] text-ink"
                onSubmitEditing={saveMeal}
                returnKeyType="done"
              />
              <Pressable disabled={isSavingMeal} onPress={saveMeal}>
                <Text className="text-[14px] font-medium text-muted">
                  {isSavingMeal ? 'Saving' : 'Save'}
                </Text>
              </Pressable>
            </View>
          </View>
        </Animated.View>

        <ScrollView
          className="flex-1 bg-white"
          contentContainerClassName="px-6 pb-20 pt-1"
          keyboardShouldPersistTaps="handled">
          {errorMessage ? (
            <View className="mb-4 rounded-[18px] bg-[#f7ece7] px-4 py-3">
              <Text className="text-[14px] leading-5 text-[#a1583d]">{errorMessage}</Text>
            </View>
          ) : null}

          {isLoadingMeals ? (
            <View className="flex-row items-center gap-3 py-4">
              <ActivityIndicator size="small" color="#8A847C" />
              <Text className="text-[15px] text-muted">Loading meals...</Text>
            </View>
          ) : null}

          {!isLoadingMeals && meals.length === 0 ? (
            <Text className="py-4 text-[16px] text-[#b8b4ad]">
              Pull down to log your first meal.
            </Text>
          ) : null}

          <View className="gap-4">
            {meals.map((meal) => (
              <View key={meal.meal_id} className="py-2">
                <Text className="text-[18px] leading-[22px] tracking-[0.1px] text-ink">
                  {meal.meal_description || 'Meal log'}
                </Text>
                <Text className="mt-1 text-[15px] text-muted">
                  {new Date(meal.time_stamp).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </Text>
                <Text className="mt-2 text-[14px] text-[#9a948b]">
                  {Object.keys(meal.nutrient_exposure || {}).length} nutrient signals logged
                </Text>
              </View>
            ))}
          </View>
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

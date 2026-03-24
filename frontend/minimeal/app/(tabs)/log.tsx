import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as Haptics from 'expo-haptics';
import { Ionicons } from '@expo/vector-icons';
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
const ACTIONS_WIDTH = 168;

type MealLogEntry = {
  meal_id: string;
  time_stamp: string;
  meal_description?: string | null;
  nutrient_exposure: Record<string, number>;
  excluded_from_daily_summary: boolean;
};

type MealListItem = MealLogEntry & {
  source: 'synced' | 'draft';
  draftText?: string;
  isSelected?: boolean;
  isSyncing?: boolean;
};

type MealCreateResponse = {
  processed_meal: {
    meal_description?: string | null;
  };
  nutrient_exposure: Record<string, number>;
  log_entry: MealLogEntry;
};

type MealGroup = {
  dateLabel: string;
  items: MealListItem[];
};

function buildDraftMeal(mealText: string): MealListItem {
  return {
    meal_id: `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    time_stamp: new Date().toISOString(),
    meal_description: mealText,
    nutrient_exposure: {},
    excluded_from_daily_summary: false,
    source: 'draft',
    draftText: mealText,
    isSelected: false,
    isSyncing: false,
  };
}

function MealRow({
  meal,
  isAnotherRowOpen,
  isOpen,
  isDeleting,
  isSelectionMode,
  isTogglingExclude,
  onToggleExcluded,
  onDelete,
  onOpen,
  onToggleSelected,
}: {
  meal: MealListItem;
  isAnotherRowOpen: boolean;
  isOpen: boolean;
  isDeleting: boolean;
  isSelectionMode: boolean;
  isTogglingExclude: boolean;
  onToggleExcluded: (mealId: string) => void;
  onDelete: (mealId: string) => void;
  onOpen: (mealId: string | null) => void;
  onToggleSelected: (mealId: string) => void;
}) {
  const swipeX = useRef(new Animated.Value(0)).current;

  const closeRow = useCallback(() => {
    Animated.spring(swipeX, {
      toValue: 0,
      useNativeDriver: true,
      tension: 180,
      friction: 18,
      overshootClamping: false,
    }).start();
  }, [swipeX]);

  const openRow = useCallback(() => {
    Animated.spring(swipeX, {
      toValue: -ACTIONS_WIDTH,
      useNativeDriver: true,
      tension: 170,
      friction: 20,
      overshootClamping: false,
    }).start();
  }, [swipeX]);

  useEffect(() => {
    if (isOpen) {
      openRow();
      return;
    }

    closeRow();
  }, [closeRow, isAnotherRowOpen, isOpen, openRow]);

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, gestureState) => {
          const isHorizontal = Math.abs(gestureState.dx) > Math.abs(gestureState.dy);
          return isHorizontal && Math.abs(gestureState.dx) > 12;
        },
        onPanResponderMove: (_, gestureState) => {
          const baseX = isOpen ? -ACTIONS_WIDTH : 0;
          const nextX = Math.max(-ACTIONS_WIDTH, Math.min(0, baseX + gestureState.dx));
          swipeX.setValue(nextX);
        },
        onPanResponderRelease: (_, gestureState) => {
          const finalX = (isOpen ? -ACTIONS_WIDTH : 0) + gestureState.dx;
          const shouldOpen = finalX <= -ACTIONS_WIDTH / 2;

          if (shouldOpen) {
            onOpen(meal.meal_id);
            openRow();
            return;
          }

          onOpen(null);
          closeRow();
        },
        onPanResponderTerminate: () => {
          if (isOpen) {
            openRow();
            return;
          }

          closeRow();
        },
      }),
    [closeRow, isOpen, meal.meal_id, onOpen, openRow, swipeX]
  );

  const handleRowPress = useCallback(() => {
    if (!isOpen) {
      return;
    }

    onOpen(null);
    closeRow();
  }, [closeRow, isOpen, onOpen]);

  const handleActionPress = useCallback(
    (action: 'exclude' | 'edit' | 'delete') => {
      if (action === 'exclude') {
        onToggleExcluded(meal.meal_id);
        onOpen(null);
        closeRow();
        return;
      }

      if (action === 'delete') {
        onDelete(meal.meal_id);
        return;
      }

      onOpen(null);
      closeRow();
    },
    [closeRow, meal.meal_id, onDelete, onOpen, onToggleExcluded]
  );

  return (
    <View className="relative w-full overflow-hidden">
      <View
        className="absolute bottom-0 right-0 top-0 flex-row items-center justify-end"
        style={{ width: ACTIONS_WIDTH }}>
        <Pressable
          className="h-full w-14 items-center justify-center"
          disabled={isTogglingExclude || meal.isSyncing}
          onPress={() => handleActionPress('exclude')}>
          <Ionicons
            name="remove-circle-outline"
            size={20}
            color={
              isTogglingExclude || meal.isSyncing
                ? '#c9beb7'
                : meal.excluded_from_daily_summary
                  ? '#a1583d'
                  : '#8A847C'
            }
          />
        </Pressable>
        <Pressable
          className="h-full w-14 items-center justify-center"
          onPress={() => handleActionPress('edit')}>
          <Ionicons name="create-outline" size={20} color="#8A847C" />
        </Pressable>
        <Pressable
          className="h-full w-14 items-center justify-center"
          disabled={isDeleting || meal.isSyncing}
          onPress={() => handleActionPress('delete')}>
          <Ionicons
            name="trash-outline"
            size={20}
            color={isDeleting || meal.isSyncing ? '#c9beb7' : '#a1583d'}
          />
        </Pressable>
      </View>

      <Animated.View
        className="w-full bg-white"
        style={{ transform: [{ translateX: swipeX }] }}
        {...panResponder.panHandlers}>
        <Pressable className="w-full" onPress={handleRowPress}>
          <View className="flex-row items-start gap-3">
            {meal.source === 'draft' && isSelectionMode ? (
              <Pressable
                className="mt-1"
                disabled={meal.isSyncing}
                onPress={() => onToggleSelected(meal.meal_id)}>
                <Ionicons
                  name={meal.isSelected ? 'checkmark-circle' : 'ellipse-outline'}
                  size={22}
                  color={meal.isSelected ? '#a1583d' : '#b8b4ad'}
                />
              </Pressable>
            ) : null}

            <View className="flex-1">
              <View className="flex-row items-center justify-between gap-3">
                <Text className="flex-1 text-[18px] leading-[22px] tracking-[0.1px] text-ink">
                  {meal.meal_description || 'Meal log'}
                </Text>

                <View
                  className={`rounded-full px-3 py-1 ${
                    meal.source === 'draft' ? 'bg-[#f7ece7]' : 'bg-[#f3f1ec]'
                  }`}>
                  <Text
                    className={`text-[12px] font-medium uppercase tracking-[1.2px] ${
                      meal.source === 'draft' ? 'text-[#a1583d]' : 'text-muted'
                    }`}>
                    {meal.isSyncing
                      ? 'Syncing'
                      : meal.excluded_from_daily_summary
                        ? 'Excluded'
                        : meal.source === 'draft'
                          ? 'Unsynced'
                          : 'Synced'}
                  </Text>
                </View>
              </View>

              <Text className="mt-1 text-[15px] text-muted">
                {new Date(meal.time_stamp).toLocaleTimeString([], {
                  hour: 'numeric',
                  minute: '2-digit',
                })}
              </Text>
            </View>
          </View>
        </Pressable>
      </Animated.View>
    </View>
  );
}

export default function LogScreen() {
  const isFocused = useIsFocused();
  const pullY = useRef(new Animated.Value(0)).current;
  const inputRef = useRef<TextInput>(null);
  const isAtTopRef = useRef(true);
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [mealText, setMealText] = useState('');
  const [meals, setMeals] = useState<MealListItem[]>([]);
  const [isLoadingMeals, setIsLoadingMeals] = useState(false);
  const [isAddingMeal, setIsAddingMeal] = useState(false);
  const [deletingMealId, setDeletingMealId] = useState<string | null>(null);
  const [togglingExcludeMealId, setTogglingExcludeMealId] = useState<string | null>(null);
  const [isSyncingSelection, setIsSyncingSelection] = useState(false);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [isSyncControlsOpen, setIsSyncControlsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [openMealId, setOpenMealId] = useState<string | null>(null);

  const groupedMeals = useMemo<MealGroup[]>(() => {
    const groups: MealGroup[] = [];
    let lastDateLabel: string | null = null;

    for (const meal of meals) {
      const date = new Date(meal.time_stamp);
      const dateLabel = date.toLocaleDateString([], {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });

      if (dateLabel !== lastDateLabel) {
        groups.push({
          dateLabel,
          items: [meal],
        });
        lastDateLabel = dateLabel;
        continue;
      }

      groups[groups.length - 1].items.push(meal);
    }

    return groups;
  }, [meals]);

  const draftMeals = useMemo(
    () => meals.filter((meal) => meal.source === 'draft'),
    [meals]
  );

  const selectedDraftCount = useMemo(
    () => draftMeals.filter((meal) => meal.isSelected).length,
    [draftMeals]
  );

  const hasDraftMeals = draftMeals.length > 0;

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
      const syncedMeals: MealListItem[] = data
        .slice()
        .reverse()
        .map((meal) => ({
          ...meal,
          excluded_from_daily_summary: meal.excluded_from_daily_summary ?? false,
          source: 'synced',
          isSelected: false,
          isSyncing: false,
        }));

      setMeals((current) => {
        const drafts = current.filter((meal) => meal.source === 'draft');
        return [...drafts, ...syncedMeals];
      });
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
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    setIsOpen(true);
    setIsClosing(false);
    animateOpen();
  }, [animateOpen]);

  const closeInput = useCallback(() => {
    setIsOpen(false);
    setIsClosing(true);
    animateClosed(() => {
      setIsClosing(false);
    });
  }, [animateClosed]);

  const pullResponder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponderCapture: (_, gestureState) =>
          !isOpen &&
          !isClosing &&
          isAtTopRef.current &&
          gestureState.dy > 8 &&
          Math.abs(gestureState.dy) > Math.abs(gestureState.dx),
        onPanResponderMove: (_, gestureState) => {
          if (isOpen || isClosing) {
            return;
          }

          pullY.setValue(clampPull(gestureState.dy));
        },
        onPanResponderRelease: (_, gestureState) => {
          if (isOpen || isClosing) {
            return;
          }

          const pulledDistance = clampPull(gestureState.dy);

          if (pulledDistance >= OPEN_THRESHOLD) {
            openInput();
            return;
          }

          animateClosed();
        },
        onPanResponderTerminate: () => {
          if (isOpen || isClosing) {
            return;
          }

          animateClosed();
        },
      }),
    [animateClosed, isClosing, isOpen, openInput, pullY]
  );

  const addMeal = useCallback(() => {
    const trimmedMeal = mealText.trim();

    if (!trimmedMeal) {
      setErrorMessage('Type a meal before adding it.');
      return;
    }

    setIsAddingMeal(true);
    setErrorMessage(null);
    setMeals((current) => [buildDraftMeal(trimmedMeal), ...current]);
    setMealText('');
    closeInput();
    setIsAddingMeal(false);
  }, [closeInput, mealText]);

  const toggleMealSelected = useCallback((mealId: string) => {
    setMeals((current) =>
      current.map((meal) =>
        meal.meal_id === mealId && meal.source === 'draft'
          ? { ...meal, isSelected: !meal.isSelected }
          : meal
      )
    );
  }, []);

  const enterSelectionMode = useCallback(() => {
    setIsSyncControlsOpen(true);
    setIsSelectionMode(true);
    setMeals((current) =>
      current.map((meal) =>
        meal.source === 'draft' ? { ...meal, isSelected: false } : meal
      )
    );
  }, []);

  const exitSelectionMode = useCallback(() => {
    setIsSelectionMode(false);
    setMeals((current) =>
      current.map((meal) =>
        meal.source === 'draft' ? { ...meal, isSelected: false } : meal
      )
    );
  }, []);

  const syncMeal = useCallback(async (mealId: string) => {
    const mealToSync = meals.find((meal) => meal.meal_id === mealId && meal.source === 'draft');

    if (!mealToSync || !mealToSync.draftText) {
      return;
    }

    setMeals((current) =>
      current.map((meal) =>
        meal.meal_id === mealId ? { ...meal, isSyncing: true } : meal
      )
    );

    try {
      const response = await fetch(`${API_BASE_URL}/meals`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_meal: mealToSync.draftText,
          tz_name: Intl.DateTimeFormat().resolvedOptions().timeZone,
          excluded_from_daily_summary: mealToSync.excluded_from_daily_summary,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Failed to sync meal (${response.status})`);
      }

      const data: MealCreateResponse = await response.json();
      const syncedMeal: MealListItem = {
        ...data.log_entry,
        source: 'synced',
        isSelected: false,
        isSyncing: false,
      };

      setMeals((current) =>
        current.map((meal) => (meal.meal_id === mealId ? syncedMeal : meal))
      );
    } catch (error) {
      setMeals((current) =>
        current.map((meal) =>
          meal.meal_id === mealId ? { ...meal, isSyncing: false } : meal
        )
      );

      throw error;
    }
  }, [meals]);

  const syncSelectedMeals = useCallback(async (mode: 'selected' | 'all') => {
    const targetMeals = meals.filter(
      (meal) =>
        meal.source === 'draft' &&
        !meal.isSyncing &&
        (mode === 'all' || meal.isSelected)
    );

    if (targetMeals.length === 0) {
      setErrorMessage(
        mode === 'selected'
          ? 'Select at least one draft meal to sync.'
          : 'There are no draft meals to sync.'
      );
      return;
    }

    setIsSyncingSelection(true);
    setErrorMessage(null);

    try {
      for (const meal of targetMeals) {
        await syncMeal(meal.meal_id);
      }

      if (mode === 'selected') {
        exitSelectionMode();
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to sync meals.');
    } finally {
      setIsSyncingSelection(false);
    }
  }, [exitSelectionMode, meals, syncMeal]);

  const deleteMeal = useCallback(async (mealId: string) => {
    const mealToDelete = meals.find((meal) => meal.meal_id === mealId);

    if (!mealToDelete) {
      return;
    }

    setOpenMealId(null);

    if (mealToDelete.source === 'draft') {
      setMeals((current) => current.filter((meal) => meal.meal_id !== mealId));
      return;
    }

    setDeletingMealId(mealId);
    setErrorMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/meals/${mealId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Failed to delete meal (${response.status})`);
      }

      setMeals((current) => current.filter((meal) => meal.meal_id !== mealId));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to delete meal.');
    } finally {
      setDeletingMealId((current) => (current === mealId ? null : current));
    }
  }, [meals]);

  const toggleMealExcluded = useCallback(async (mealId: string) => {
    const mealToToggle = meals.find((meal) => meal.meal_id === mealId);

    if (!mealToToggle) {
      return;
    }

    const nextExcludedState = !mealToToggle.excluded_from_daily_summary;

    if (mealToToggle.source === 'draft') {
      setMeals((current) =>
        current.map((meal) =>
          meal.meal_id === mealId
            ? { ...meal, excluded_from_daily_summary: nextExcludedState }
            : meal
        )
      );
      return;
    }

    setTogglingExcludeMealId(mealId);
    setErrorMessage(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/meals/${mealId}/exclude?excluded_from_daily_summary=${nextExcludedState}`,
        {
          method: 'PATCH',
        }
      );

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Failed to update meal (${response.status})`);
      }

      const updatedMeal: MealLogEntry = await response.json();
      setMeals((current) =>
        current.map((meal) =>
          meal.meal_id === mealId
            ? {
                ...meal,
                ...updatedMeal,
                source: 'synced',
                isSelected: false,
                isSyncing: false,
              }
            : meal
        )
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to update meal.');
    } finally {
      setTogglingExcludeMealId((current) => (current === mealId ? null : current));
    }
  }, [meals]);

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top', 'bottom']}>
      <View className="flex-1 bg-white" {...pullResponder.panHandlers}>
        {isOpen ? (
          <Pressable
            className="absolute bottom-0 left-0 right-0 z-10 bg-transparent"
            style={{ top: REVEAL_HEIGHT }}
            onPress={closeInput}
          />
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
                onSubmitEditing={addMeal}
                returnKeyType="done"
              />
              <Pressable disabled={isAddingMeal} onPress={addMeal}>
                <Text className="text-[14px] font-medium text-muted">
                  {isAddingMeal ? 'Adding' : 'Add'}
                </Text>
              </Pressable>
            </View>
          </View>
        </Animated.View>

        <ScrollView
          className="flex-1 bg-white"
          contentContainerClassName="px-6 pb-32 pt-5"
          keyboardShouldPersistTaps="handled"
          onScroll={(event) => {
            const offsetY = event.nativeEvent.contentOffset.y;
            isAtTopRef.current = offsetY <= 0;
          }}
          scrollEventThrottle={16}
          onScrollBeginDrag={() => {
            setOpenMealId(null);
            if (!isSelectionMode) {
              setIsSyncControlsOpen(false);
            }
          }}>
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
              Pull down to add your first meal.
            </Text>
          ) : null}

          <View className="gap-6">
            {groupedMeals.map((group) => (
              <View key={group.dateLabel}>
                <Text className="mb-3 text-[16px] text-muted">{group.dateLabel}</Text>
                <View className="gap-4">
                  {group.items.map((meal) => (
                    <MealRow
                      key={meal.meal_id}
                      meal={meal}
                      isDeleting={deletingMealId === meal.meal_id}
                      isAnotherRowOpen={openMealId !== null && openMealId !== meal.meal_id}
                      isOpen={openMealId === meal.meal_id}
                      isSelectionMode={isSelectionMode}
                      isTogglingExclude={togglingExcludeMealId === meal.meal_id}
                      onDelete={deleteMeal}
                      onOpen={setOpenMealId}
                      onToggleExcluded={toggleMealExcluded}
                      onToggleSelected={toggleMealSelected}
                    />
                  ))}
                </View>
              </View>
            ))}
          </View>
        </ScrollView>

        <View className="border-t border-line bg-white px-6 pb-1 pt-2">
          <View className="flex-row items-center justify-between gap-3">
            <Pressable
              className="h-9 w-9 items-center justify-center rounded-full border border-line bg-white"
              disabled={isSyncingSelection}
              onPress={() => setIsSyncControlsOpen((current) => !current)}>
              <Ionicons
                name={isSyncControlsOpen ? 'close-outline' : 'sync-outline'}
                size={16}
                color="#8A847C"
              />
            </Pressable>

            {isSyncControlsOpen ? (
              <View className="flex-1 flex-row items-center justify-end gap-3">
                {isSelectionMode ? (
                  <>
                    <Text className="mr-auto text-[14px] text-muted">
                      {selectedDraftCount} selected
                    </Text>
                    <Pressable
                      className="rounded-full border border-line bg-white px-4 py-2.5"
                      disabled={isSyncingSelection}
                      onPress={exitSelectionMode}>
                      <Text className="text-[14px] font-medium text-ink">Done</Text>
                    </Pressable>
                    <Pressable
                      className={`rounded-full px-4 py-2.5 ${
                        selectedDraftCount > 0 && !isSyncingSelection
                          ? 'bg-ink'
                          : 'bg-[#d9d4cc]'
                      }`}
                      disabled={selectedDraftCount === 0 || isSyncingSelection}
                      onPress={() => syncSelectedMeals('selected')}>
                      <Text className="text-[14px] font-medium text-white">
                        {isSyncingSelection ? 'Syncing...' : 'Sync selected'}
                      </Text>
                    </Pressable>
                  </>
                ) : (
                  <>
                    <Pressable
                      className={`rounded-full border px-4 py-2.5 ${
                        hasDraftMeals ? 'border-line bg-white' : 'border-[#d9d4cc] bg-[#f3f1ec]'
                      }`}
                      disabled={isSyncingSelection || !hasDraftMeals}
                      onPress={enterSelectionMode}>
                      <Text className="text-[14px] font-medium text-ink">Select</Text>
                    </Pressable>
                    <Pressable
                      className={`rounded-full px-4 py-2.5 ${
                        hasDraftMeals && !isSyncingSelection ? 'bg-ink' : 'bg-[#d9d4cc]'
                      }`}
                      disabled={isSyncingSelection || !hasDraftMeals}
                      onPress={() => syncSelectedMeals('all')}>
                      <Text className="text-[14px] font-medium text-white">
                        {isSyncingSelection ? 'Syncing...' : 'Sync all'}
                      </Text>
                    </Pressable>
                  </>
                )}
              </View>
            ) : (
              <View />
            )}
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as Haptics from 'expo-haptics';
import { ActivityIndicator, Animated, PanResponder, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useIsFocused } from '@react-navigation/native';

import { MealComposer } from '@/components/log/meal-composer';
import { buildDraftMeal, clampPull, groupMealsByDate, OPEN_THRESHOLD, REVEAL_HEIGHT } from '@/components/log/helpers';
import { MealRow } from '@/components/log/meal-row';
import { SyncControls } from '@/components/log/sync-controls';
import { EditingMealState, MealCreateResponse, MealListItem, MealLogEntry } from '@/components/log/types';
import { API_BASE_URL } from '@/constants/api';

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
  const [editingMeal, setEditingMeal] = useState<EditingMealState | null>(null);
  const [deletingMealId, setDeletingMealId] = useState<string | null>(null);
  const [togglingExcludeMealId, setTogglingExcludeMealId] = useState<string | null>(null);
  const [isSyncingSelection, setIsSyncingSelection] = useState(false);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [isSyncControlsOpen, setIsSyncControlsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [openMealId, setOpenMealId] = useState<string | null>(null);

  const groupedMeals = useMemo(() => groupMealsByDate(meals), [meals]);
  const draftMeals = useMemo(() => meals.filter((meal) => meal.source === 'draft'), [meals]);
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
    setEditingMeal(null);
    setMealText('');
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

  const submitMeal = useCallback(async () => {
    const trimmedMeal = mealText.trim();

    if (!trimmedMeal) {
      setErrorMessage(editingMeal ? 'Type a new meal before saving it.' : 'Type a meal before adding it.');
      return;
    }

    if (
      editingMeal &&
      trimmedMeal.toLocaleLowerCase() === editingMeal.originalDescription.trim().toLocaleLowerCase()
    ) {
      setErrorMessage('Enter a meal that is different from the original.');
      return;
    }

    setIsAddingMeal(true);
    setErrorMessage(null);

    try {
      if (!editingMeal) {
        setMeals((current) => [buildDraftMeal(trimmedMeal), ...current]);
        closeInput();
        return;
      }

      if (editingMeal.source === 'synced') {
        const response = await fetch(`${API_BASE_URL}/meals/${editingMeal.mealId}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          const detail = await response.text();
          throw new Error(detail || `Failed to prepare meal edit (${response.status})`);
        }
      }

      setMeals((current) =>
        current.map((meal) =>
          meal.meal_id === editingMeal.mealId
            ? {
                ...meal,
                meal_description: trimmedMeal,
                time_stamp: editingMeal.originalTimestamp,
                nutrient_exposure: {},
                excluded_from_daily_summary: false,
                source: 'draft',
                draftText: trimmedMeal,
                isSelected: false,
                isSyncing: false,
              }
            : meal
        )
      );
      closeInput();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to update meal.');
    } finally {
      setIsAddingMeal(false);
    }
  }, [closeInput, editingMeal, mealText]);

  const toggleMealSelected = useCallback((mealId: string) => {
    setMeals((current) =>
      current.map((meal) =>
        meal.meal_id === mealId && meal.source === 'draft'
          ? { ...meal, isSelected: !meal.isSelected }
          : meal
      )
    );
  }, []);

  const startEditingMeal = useCallback((mealId: string) => {
    const mealToEdit = meals.find((meal) => meal.meal_id === mealId);

    if (!mealToEdit) {
      return;
    }

    setErrorMessage(null);
    setEditingMeal({
      mealId,
      originalDescription: mealToEdit.meal_description ?? '',
      originalTimestamp: mealToEdit.time_stamp,
      source: mealToEdit.source,
    });
    setMealText(mealToEdit.meal_description ?? '');
    openInput();
  }, [meals, openInput]);

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

        <MealComposer
          inputRef={inputRef}
          mealText={mealText}
          setMealText={setMealText}
          editingMeal={editingMeal}
          isAddingMeal={isAddingMeal}
          pullY={pullY}
          onSubmit={() => {
            void submitMeal();
          }}
        />

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
                      onEdit={startEditingMeal}
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

        <SyncControls
          hasDraftMeals={hasDraftMeals}
          isSyncControlsOpen={isSyncControlsOpen}
          isSelectionMode={isSelectionMode}
          isSyncingSelection={isSyncingSelection}
          selectedDraftCount={selectedDraftCount}
          onToggleOpen={() => setIsSyncControlsOpen((current) => !current)}
          onEnterSelectionMode={enterSelectionMode}
          onExitSelectionMode={exitSelectionMode}
          onSyncAll={() => {
            void syncSelectedMeals('all');
          }}
          onSyncSelected={() => {
            void syncSelectedMeals('selected');
          }}
        />
      </View>
    </SafeAreaView>
  );
}

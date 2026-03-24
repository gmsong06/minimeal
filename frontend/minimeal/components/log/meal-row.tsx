import { useCallback, useEffect, useMemo, useRef } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Animated, PanResponder, Pressable, Text, View } from 'react-native';

import { ACTIONS_WIDTH } from '@/components/log/helpers';
import { MealListItem } from '@/components/log/types';

type MealRowProps = {
  meal: MealListItem;
  isAnotherRowOpen: boolean;
  isOpen: boolean;
  isDeleting: boolean;
  isSelectionMode: boolean;
  isTogglingExclude: boolean;
  onEdit: (mealId: string) => void;
  onToggleExcluded: (mealId: string) => void;
  onDelete: (mealId: string) => void;
  onOpen: (mealId: string | null) => void;
  onToggleSelected: (mealId: string) => void;
};

export function MealRow({
  meal,
  isAnotherRowOpen,
  isOpen,
  isDeleting,
  isSelectionMode,
  isTogglingExclude,
  onEdit,
  onToggleExcluded,
  onDelete,
  onOpen,
  onToggleSelected,
}: MealRowProps) {
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

      if (action === 'edit') {
        onEdit(meal.meal_id);
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
    [closeRow, meal.meal_id, onDelete, onEdit, onOpen, onToggleExcluded]
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

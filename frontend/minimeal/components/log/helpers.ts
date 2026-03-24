import { MealGroup, MealListItem } from '@/components/log/types';

export const REVEAL_HEIGHT = 50;
export const OPEN_THRESHOLD = 40;
export const ACTIONS_WIDTH = 168;

export function buildDraftMeal(mealText: string): MealListItem {
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

export function groupMealsByDate(meals: MealListItem[]): MealGroup[] {
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
}

export function clampPull(distance: number) {
  return Math.max(0, Math.min(REVEAL_HEIGHT, distance));
}

export type MealLogEntry = {
  meal_id: string;
  time_stamp: string;
  meal_description?: string | null;
  nutrient_exposure: Record<string, number>;
  excluded_from_daily_summary: boolean;
};

export type MealListItem = MealLogEntry & {
  source: 'synced' | 'draft';
  draftText?: string;
  isSelected?: boolean;
  isSyncing?: boolean;
};

export type MealCreateResponse = {
  processed_meal: {
    meal_description?: string | null;
  };
  nutrient_exposure: Record<string, number>;
  log_entry: MealLogEntry;
};

export type MealGroup = {
  dateLabel: string;
  items: MealListItem[];
};

export type EditingMealState = {
  mealId: string;
  originalDescription: string;
  originalTimestamp: string;
  source: MealListItem['source'];
};

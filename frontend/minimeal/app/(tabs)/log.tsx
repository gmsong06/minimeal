import { useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';

import { API_BASE_URL } from '@/constants/api';

type LoggedFood = {
  name: string;
  portion_class?: string | null;
};

type MealCreateResponse = {
  processed_meal: {
    meal_description?: string | null;
    foods?: LoggedFood[];
    notes?: string[];
  };
  nutrient_exposure: Record<string, number>;
  log_entry: {
    meal_id: string;
    meal_description?: string | null;
    time_stamp: string;
    foods: LoggedFood[];
  };
};

const prompts = [
  '2 eggs, sourdough toast, and berries',
  'chicken bowl with rice, cucumbers, and tahini',
  'matcha latte and a banana before class',
];

export default function LogScreen() {
  const [mealText, setMealText] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [savedMeal, setSavedMeal] = useState<MealCreateResponse | null>(null);

  async function submitMeal() {
    const trimmedMeal = mealText.trim();

    if (!trimmedMeal) {
      setErrorMessage('Add a short meal description before saving.');
      return;
    }

    setIsSaving(true);
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
        throw new Error(detail || `Request failed with ${response.status}`);
      }

      const data: MealCreateResponse = await response.json();
      setSavedMeal(data);
      setMealText('');
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Something went wrong while saving this meal.'
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <ScrollView className="flex-1 bg-canvas" contentContainerClassName="px-6 pb-28 pt-20">
      <View className="mb-10 gap-4">
        <Text className="text-[42px] font-medium tracking-[-1.2px] text-ink">Log meal</Text>
        <Text className="max-w-[315px] text-[18px] leading-7 text-muted">
          Capture what you ate in natural language. Keep it fast, low-pressure, and close to how
          you would actually describe a meal.
        </Text>
      </View>

      <View className="mb-6 rounded-card border border-line bg-card px-5 py-5 shadow-float">
        <Text className="mb-4 text-[14px] uppercase tracking-[2px] text-muted">
          Today&apos;s entry
        </Text>
        <TextInput
          multiline
          placeholder="Try: salmon bowl with rice, avocado, cucumber, and miso sauce"
          placeholderTextColor="#b3aea6"
          textAlignVertical="top"
          value={mealText}
          onChangeText={setMealText}
          className="min-h-[180px] rounded-[24px] bg-[#f3f1ec] px-5 py-5 text-[20px] leading-8 text-ink"
        />

        <View className="mt-5 flex-row items-center justify-between">
          <Text className="max-w-[190px] text-[15px] leading-6 text-muted">
            No macros, no pressure. Just enough detail to be useful.
          </Text>
          <Pressable
            className="rounded-full border border-line bg-white px-5 py-3"
            disabled={isSaving}
            onPress={submitMeal}>
            <Text className="text-[16px] font-medium text-ink">
              {isSaving ? 'Saving...' : 'Save meal'}
            </Text>
          </Pressable>
        </View>

        {errorMessage ? (
          <Text className="mt-4 text-[15px] leading-6 text-[#b26545]">{errorMessage}</Text>
        ) : null}
      </View>

      {savedMeal ? (
        <View className="mb-6 rounded-card border border-line bg-card px-5 py-5">
          <Text className="mb-4 text-[14px] uppercase tracking-[2px] text-muted">
            Saved just now
          </Text>
          <Text className="text-[28px] tracking-[-0.6px] text-ink">
            {savedMeal.log_entry.meal_description || 'Meal logged'}
          </Text>
          <Text className="mt-2 text-[15px] leading-6 text-muted">
            {savedMeal.log_entry.foods.length} foods recognized
          </Text>

          <View className="mt-4 gap-3">
            {savedMeal.log_entry.foods.map((food) => (
              <View
                key={`${savedMeal.log_entry.meal_id}-${food.name}`}
                className="rounded-[22px] bg-[#f3f1ec] px-4 py-4">
                <Text className="text-[18px] text-ink">{food.name}</Text>
                {food.portion_class ? (
                  <Text className="mt-1 text-[14px] uppercase tracking-[1.6px] text-muted">
                    {food.portion_class}
                  </Text>
                ) : null}
              </View>
            ))}
          </View>

          {savedMeal.processed_meal.notes && savedMeal.processed_meal.notes.length > 0 ? (
            <View className="mt-4 rounded-[22px] bg-accentSoft px-4 py-4">
              <Text className="mb-2 text-[14px] uppercase tracking-[1.6px] text-muted">Notes</Text>
              {savedMeal.processed_meal.notes.map((note) => (
                <Text key={note} className="text-[15px] leading-6 text-ink">
                  {note}
                </Text>
              ))}
            </View>
          ) : null}
        </View>
      ) : null}

      <View className="rounded-card border border-line bg-card px-5 py-5">
        <Text className="mb-4 text-[14px] uppercase tracking-[2px] text-muted">Prompt ideas</Text>
        {prompts.map((prompt) => (
          <Pressable
            key={prompt}
            className="border-b border-line py-4 last:border-b-0"
            onPress={() => setMealText(prompt)}>
            <Text className="text-[20px] leading-8 tracking-[-0.4px] text-ink">{prompt}</Text>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

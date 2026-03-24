import { Dispatch, RefObject, SetStateAction } from 'react';
import { Animated, Pressable, Text, TextInput, View } from 'react-native';

import { REVEAL_HEIGHT } from '@/components/log/helpers';
import { EditingMealState } from '@/components/log/types';

type MealComposerProps = {
  inputRef: RefObject<TextInput | null>;
  mealText: string;
  setMealText: Dispatch<SetStateAction<string>>;
  editingMeal: EditingMealState | null;
  isAddingMeal: boolean;
  pullY: Animated.Value;
  onSubmit: () => void;
};

export function MealComposer({
  inputRef,
  mealText,
  setMealText,
  editingMeal,
  isAddingMeal,
  pullY,
  onSubmit,
}: MealComposerProps) {
  return (
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
            placeholder={editingMeal ? 'Update meal...' : 'I ate...'}
            placeholderTextColor="#b8b4ad"
            className="flex-1 text-[18px] leading-[22px] tracking-[0.1px] text-ink"
            onSubmitEditing={onSubmit}
            returnKeyType="done"
          />
          <Pressable disabled={isAddingMeal} onPress={onSubmit}>
            <Text className="text-[14px] font-medium text-muted">
              {isAddingMeal ? (editingMeal ? 'Saving' : 'Adding') : editingMeal ? 'Save' : 'Add'}
            </Text>
          </Pressable>
        </View>
      </View>
    </Animated.View>
  );
}

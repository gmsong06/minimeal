import { Ionicons } from '@expo/vector-icons';
import { Pressable, Text, View } from 'react-native';

type SyncControlsProps = {
  hasDraftMeals: boolean;
  isSyncControlsOpen: boolean;
  isSelectionMode: boolean;
  isSyncingSelection: boolean;
  selectedDraftCount: number;
  onToggleOpen: () => void;
  onEnterSelectionMode: () => void;
  onExitSelectionMode: () => void;
  onSyncAll: () => void;
  onSyncSelected: () => void;
};

export function SyncControls({
  hasDraftMeals,
  isSyncControlsOpen,
  isSelectionMode,
  isSyncingSelection,
  selectedDraftCount,
  onToggleOpen,
  onEnterSelectionMode,
  onExitSelectionMode,
  onSyncAll,
  onSyncSelected,
}: SyncControlsProps) {
  return (
    <View className="border-t border-line bg-white px-6 pb-1 pt-2">
      <View className="flex-row items-center justify-between gap-3">
        <Pressable
          className="h-9 w-9 items-center justify-center rounded-full border border-line bg-white"
          disabled={isSyncingSelection}
          onPress={onToggleOpen}>
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
                <Text className="mr-auto text-[14px] text-muted">{selectedDraftCount} selected</Text>
                <Pressable
                  className="rounded-full border border-line bg-white px-4 py-2.5"
                  disabled={isSyncingSelection}
                  onPress={onExitSelectionMode}>
                  <Text className="text-[14px] font-medium text-ink">Done</Text>
                </Pressable>
                <Pressable
                  className={`rounded-full px-4 py-2.5 ${
                    selectedDraftCount > 0 && !isSyncingSelection ? 'bg-ink' : 'bg-[#d9d4cc]'
                  }`}
                  disabled={selectedDraftCount === 0 || isSyncingSelection}
                  onPress={onSyncSelected}>
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
                  onPress={onEnterSelectionMode}>
                  <Text className="text-[14px] font-medium text-ink">Select</Text>
                </Pressable>
                <Pressable
                  className={`rounded-full px-4 py-2.5 ${
                    hasDraftMeals && !isSyncingSelection ? 'bg-ink' : 'bg-[#d9d4cc]'
                  }`}
                  disabled={isSyncingSelection || !hasDraftMeals}
                  onPress={onSyncAll}>
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
  );
}

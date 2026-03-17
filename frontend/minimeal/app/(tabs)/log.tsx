import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  PanResponder,
  Pressable,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

const REVEAL_HEIGHT = 50;
const OPEN_THRESHOLD = 40;

export default function LogScreen() {
  const pullY = useRef(new Animated.Value(0)).current;
  const inputRef = useRef<TextInput>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [mealText, setMealText] = useState('');

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
            console.log("Opening input")
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

  const revealedMessageOpacity = pullY.interpolate({
    inputRange: [0, OPEN_THRESHOLD, REVEAL_HEIGHT],
    outputRange: [0, 0.5, 1],
    extrapolate: 'clamp',
  });

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <View className="flex-1 bg-canvas" {...(!isOpen && !isClosing ? panResponder.panHandlers : {})}>
        {isOpen ? (
          <Pressable className="absolute inset-0 z-10 bg-transparent" onPress={closeInput} />
        ) : null}

        <Animated.View
          className="overflow-hidden px-6"
          style={{
            height: pullY,
          }}>
          <View
            className="border-b border-line bg-canvas"
            style={{
              height: REVEAL_HEIGHT,
              justifyContent: 'flex-end',
              paddingBottom: 6,
            }}>
            <TextInput
              ref={inputRef}
              value={mealText}
              onChangeText={setMealText}
              placeholder="I ate..."
              placeholderTextColor="#b8b4ad"
              className="text-[16px] leading-[22px] tracking-[-0.6px] text-ink"
            />
          </View>
        </Animated.View>

        {/* <View className="flex-1 justify-between px-6 pb-20 pt-3">
          <Animated.View style={{ opacity: revealedMessageOpacity }}>
            {isOpen ? (
              <Text className="text-[16px] text-muted">Input fully revealed</Text>
            ) : (
              <Text className="text-[16px] text-[#b8b4ad]">Pull down to reveal the input</Text>
            )}
          </Animated.View>

          <View className="pb-6">
            {mealText ? (
              <View className="self-start rounded-full bg-[#efede8] px-4 py-3">
                <Text className="text-[15px] text-muted">{mealText}</Text>
              </View>
            ) : null}
          </View>
        </View> */}
      </View>
    </SafeAreaView>
  );
}

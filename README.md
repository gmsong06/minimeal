# Nutrition Notes
Natural-language meal logging with time-aware nutrition reasoning

## Problem Statement
Most nutrition apps over-optimize for calorie tracking and precision, which increases friction and discourages use. At the same time, micronutrient intake, which strongly affects daily wellbeing, is underrepresented and poorly understood in media, often giving preference to macronutrients.

This project explores whether coarse, qualitative nutrition reasoning paired with natural-language input can provide actionable guidance without the psychological cost of traditional food logging.

### What this project is not
- A medical or diagnostic tool
- Not optimized for clinical accuracy
- Not for weight loss or calorie counting

## System Workflow
1. **Natural-language meal input**
   - Users enter meals informally (e.g. “broccoli cheddar soup w grilled cheese”).
   - Input is intentionally unconstrained to reduce logging friction.

2. **Meal decomposition**
   - The system extracts food components from the input
     (e.g. broccoli, cheese, bread, butter, milk).
   - This step favors reasonable approximation over exact ingredient parsing.

3. **Micronutrient mapping**
   - Each food component is mapped to a qualitative micronutrient profile
     using public nutrition reference data.
   - Nutrients are represented with general categories (low / moderate / high)
     rather than precise quantities.
    
4. **Time-sensitive nutrient tracking**
   - The system maintains a daily micronutrient state.
   - Nutrients are treated differently based on biological properties:
     - Water-soluble nutrients are assumed to reset daily.
     - Fat-soluble nutrients are more flexible because they can be stored across meals of different days.

5. **Additive guidance generation**
   - Based on the current nutrient state, the system suggests 1–3 nutrients
     or food categories to prioritize in the next meal.
      - If it is the last meal of the day, system generates a summary of nutrients consumed.
   - Suggestions are framed as additions rather than restrictions.

### Additional Goals
- Prioritize low-friction interaction over nutritional precision
- Favor additive guidance instead of restriction
- Avoid false confidence when operating on uncertain inputs
- Keep outputs interpretable to non-expert users

## Expected Limitations
- Complicated dishes or restaurant meals are simplified and may omit some foods.
- Portion size is not modeled, so a user could have hit a nutrient, but not enough to make it substantial.

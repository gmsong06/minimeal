# Minimeal
Natural-language meal logging with time-aware nutrition reasoning

## Repository Structure
- `backend/`: FastAPI backend for meal processing, USDA lookup, and nutrient reasoning
- `frontend/minimeal/`: Expo / React Native frontend

## Installation

### Backend
1. Ensure Python 3.11 is installed (matches `backend/runtime.txt`):

```bash
python3.11 --version
```

If you already created `backend/.venv` with another Python version, replace it first:

```bash
mv backend/.venv backend/.venv-backup-$(date +%Y%m%d%H%M%S)
```

2. Create and activate a virtual environment from the repo root:

```bash
cd minimeal
python3.11 -m venv backend/.venv
source backend/.venv/bin/activate
python --version
```

3. Install backend dependencies:

```bash
cd backend
python -m pip install -r requirements.txt
```

### Frontend
1. Install frontend dependencies:

```bash
cd minimeal/frontend/minimeal
npm install
```

## Environment Variables

### Backend
Set these before running the API:

- `OPENAI_API_KEY`: recommended for full AI meal parsing and nutrient selection.
  - If missing, the backend falls back to a simpler parser so meal sync still completes.
- `HF_TOKEN`: optional, but recommended for higher Hugging Face rate limits and faster model downloads
- `PORT`: optional for local development; defaults to `8000`. Render provides this automatically.
- `AWS_REGION`: defaults to `us-east-1`
- `MINIMEAL_STORAGE_MODE`: `dynamodb` or `auto` (default `auto`)
- `MINIMEAL_USERS_TABLE`: defaults to `minimeal-users`
- `MINIMEAL_MEALS_TABLE`: defaults to `minimeal-meals`

You can export them in your shell:

```bash
export OPENAI_API_KEY="your_openai_api_key"
export HF_TOKEN="your_huggingface_token"
export AWS_REGION="us-east-1"
export MINIMEAL_STORAGE_MODE="dynamodb"
export MINIMEAL_USERS_TABLE="minimeal-users"
export MINIMEAL_MEALS_TABLE="minimeal-meals"
```

Or place them in `backend/.env`.

### AWS setup (DynamoDB + seeded fake accounts)

Run this once from `backend/`:

```bash
cd minimeal/backend
source .venv/bin/activate
MINIMEAL_STORAGE_MODE=dynamodb python scripts/setup_minimeal_aws.py
```

This script creates/tags these tables if missing:
- `minimeal-users`
- `minimeal-meals`

It also seeds demo credentials:
- `minimeal_alex / minimeal123`
- `minimeal_riley / minimeal123`
- `minimeal_jordan / minimeal123`

### Frontend
The frontend currently uses the default API base URL from [`frontend/minimeal/constants/api.ts`](frontend/minimeal/constants/api.ts):

- iOS simulator: `http://127.0.0.1:8000`
- Android emulator: `http://10.0.2.2:8000`

To point at another backend, set:

```bash
export EXPO_PUBLIC_MINIMEAL_API_BASE_URL="https://your-api-url"
```

## Running The App

### Run the backend
From `backend/` with your virtual environment active:

```bash
cd minimeal/backend
python -m uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

After backend startup, sign in from the app with one of the seeded fake accounts.

### Run the frontend

```bash
cd minimeal/frontend/minimeal
npm start
```

Useful variants:

- `npm run ios`
- `npm run android`
- `npm run web`

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

## Success Metrics

### Technical metrics
Technical performance is evaluated at the level of intermediate reasoning tasks rather than end-to-end accuracy.

- **Meal decomposition quality**
  - Percentage of meals where extracted food components are judged “reasonable”
  - Error analysis of missed or hallucinated ingredients

- **Micronutrient inference correctness**
  - Given known food inputs, does the system identify plausible micronutrient coverage?
  - Emphasis is placed on minimizing false-positive nutrient claims

- **Output stability**
  - Similar meal descriptions produce similar nutrient profiles
  - Minor phrasing changes do not lead to large reasoning shifts

# Caddie Lentz

Golf score and statistics tracker. Tracks rounds hole-by-hole, logs shot data,
and surfaces the top 1-2 practice focus areas based on recent performance.

## Stack
- Streamlit (Python app framework)
- Supabase (hosted Postgres + Auth)
- Plotly (charts)
- Deployed on Streamlit Community Cloud

## Local Setup

### Windows prerequisite
Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) before running pip install. Select the "Desktop development with C++" workload. Required by some Python package dependencies.

### Steps
1. Clone the repo
2. Create a Supabase project at supabase.com
3. Run `db/migrations/001_initial_schema.sql` in the Supabase SQL editor
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your Supabase URL and anon (public) key
5. Install dependencies: `pip install -r requirements.txt`
6. Run: `streamlit run app.py`

## Running Tests

    pytest tests/ -v

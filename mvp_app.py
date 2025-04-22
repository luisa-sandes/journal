# ==============================================================================
# == COMPLETE CODE FOR mvp_app.py - FOR STREAMLIT CLOUD or LOCAL RUN ==
# ==============================================================================

# --- Imports ---
import streamlit as st
import re
import anthropic          # For Claude API
import os                 # For reading environment variables/secrets
import pandas as pd         # For Timestamp
# --- End Imports ---

# --- Page Config (MUST be FIRST Streamlit command after imports) ---
st.set_page_config(layout="wide")
# --- End Page Config ---


# --- Configure Anthropic API Key using os.environ ---
# This reads the key from Streamlit Cloud Secrets (if deployed)
# OR from a local environment variable (if running locally)

anthropic_api_configured = False
client = None # Initialize client as None globally

try:
    # Attempt to read the key from secrets/environment variables
    # IMPORTANT: You must set this secret named ANTHROPIC_API_KEY either in
    # Streamlit Cloud's settings OR as a local environment variable.
    ANTHROPIC_API_KEY = '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'

    if ANTHROPIC_API_KEY:
        # If key was found, initialize the Anthropic client object
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        anthropic_api_configured = True
        # You could add an st.info() or similar here if you want confirmation in the app
        # st.info("Anthropic client configured.", icon="✅")
    else:
        # Handle case where environment variable exists but is empty
        # This path is less likely with os.environ[] which raises KeyError if missing
        print("Warning: ANTHROPIC_API_KEY environment variable is set but empty.")
        # Error will be shown later in the UI part if needed
        anthropic_api_configured = False

except KeyError:
    # Handle case where environment variable/secret doesn't exist
    print("Warning: ANTHROPIC_API_KEY environment variable/secret not set.")
    # Error will be shown later in the UI part if needed
    anthropic_api_configured = False
except Exception as e:
    # Catch any other errors during initialization
    print(f"Error initializing Anthropic client: {e}")
    # Error will be shown later in the UI part if needed
    anthropic_api_configured = False
# --- End API Configuration ---


# --- Function Definitions ---

# Function to call Claude API for Scope Check
def ai_scope_check_claude(abstract, journal_scope):
    """Uses Anthropic Claude API to assess scope fit."""
    if not client:
         return "API Client Not Initialized", "Could not configure API Key from Secrets/Environment Variable."

    model_name = "claude-3-haiku-20240307"
    prompt = f"""
Analyze the fit between the following journal scope and paper abstract.
Focus on whether the abstract's topic, research area, and potential contribution align with the journal's stated aims.
Provide a concise assessment categorized as 'High Fit', 'Medium Fit', 'Low Fit', or 'No Fit'.
Follow this with a brief 1-2 sentence justification.

**Journal Scope:**
{journal_scope}

**Paper Abstract:**
{abstract}

**Assessment:**
"""
    try:
        message = client.messages.create(
            model=model_name,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        result_text = message.content[0].text.strip()
        # Basic Parsing
        category = "Unknown"; justification = result_text
        if "\n" in result_text:
            parts = result_text.split('\n', 1)
            category_part = parts[0].replace("**","").replace("Assessment:","").strip()
            if category_part in ['High Fit', 'Medium Fit', 'Low Fit', 'No Fit']: category = category_part
            justification = parts[1].strip() if len(parts) > 1 else result_text
        elif result_text.startswith(('High Fit', 'Medium Fit', 'Low Fit', 'No Fit')):
             for cat_label in ['High Fit', 'Medium Fit', 'Low Fit', 'No Fit']:
                 if result_text.startswith(cat_label):
                     category = cat_label; justification = result_text[len(cat_label):].strip().lstrip(':').strip(); break
        return category, justification
    except Exception as e:
        print(f"Error calling Claude API in function: {e}")
        return "API Call Error", f"Could not get assessment from AI: {e}"

# Function for Basic Formatting Checks
def check_formatting(full_text, max_word_count_str, required_sections_str):
    """Performs basic formatting checks (word count, required sections)."""
    results = {}
    word_count = len(re.findall(r'\w+', full_text))
    results['word_count'] = word_count
    try:
        max_wc = int(max_word_count_str)
        if word_count > max_wc: results['word_count_status'] = f"Exceeded limit ({max_wc})"
        else: results['word_count_status'] = "OK"
    except ValueError: results['word_count_status'] = "Invalid max word count input (must be a number)"
    required = [section.strip().lower() for section in required_sections_str.split(',') if section.strip()]
    found_sections, missing_sections = [], []
    text_lower = full_text.lower()
    for section in required:
        if re.search(r'\b' + re.escape(section) + r'\b', text_lower): found_sections.append(section.capitalize())
        else: missing_sections.append(section.capitalize())
    results['required_sections_found'] = found_sections; results['required_sections_missing'] = missing_sections
    return results
# --- End Function Definitions ---


# --- Streamlit Application UI ---
st.title("Journal Fit MVP Checker (using Claude AI)")

# Display timestamp (uses server's local time)
try:
    st.markdown(f"*{'Current time: ' + str(pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'))}*")
except Exception as e:
    st.markdown(f"*Error getting timestamp: {e}*")

# Use columns for layout
col1, col2 = st.columns(2)
with col1:
    st.header("Journal Information")
    journal_scope = st.text_area("Paste Journal Scope Description Here:", height=150)
    max_word_count = st.text_input("Max Word Count Limit:", "5000")
    required_sections = st.text_input("Required Sections (comma-separated keywords):", "Abstract, Introduction, Methods, Results, Discussion, References, Conflict of Interest")
with col2:
    st.header("Manuscript Information")
    paper_abstract = st.text_area("Paste Paper Abstract Here:", height=150)
    paper_full_text = st.text_area("Paste Full Text (or significant portion) Here:", height=300)

# --- Check Button and Results Display ---
if st.button("Check Manuscript Fit", use_container_width=True):
    if not (journal_scope and paper_abstract and paper_full_text):
        st.error("Please paste content into all Journal and Manuscript fields.")
    else:
        st.subheader("Analysis Results")
        results_col1, results_col2 = st.columns(2)
        # --- Scope Check Results ---
        with results_col1:
            st.markdown("**Scope Analysis (Claude AI)**")
            if not anthropic_api_configured:
                st.error("⚠️ AI Scope check failed: ANTHROPIC_API_KEY Secret/Environment Variable not set correctly.")
            else:
                with st.spinner("Analyzing scope with Claude AI... Please wait."):
                    scope_category, scope_justification = ai_scope_check_claude(paper_abstract, journal_scope)
                # Display results
                if scope_category == "High Fit": st.success(f"**Assessment:** {scope_category}")
                elif scope_category == "Medium Fit": st.info(f"**Assessment:** {scope_category}")
                elif scope_category == "Low Fit" or scope_category == "No Fit": st.warning(f"**Assessment:** {scope_category}")
                else: st.error(f"**Assessment:** {scope_category}")
                st.write(f"**Justification:** {scope_justification}")
        # --- Formatting Check Results ---
        with results_col2:
            st.markdown("**Formatting Checks (Basic)**")
            format_results = check_formatting(paper_full_text, max_word_count, required_sections)
            # Word Count
            wc_status = format_results['word_count_status']; wc_display = f"Word Count: {format_results['word_count']}"
            if wc_status == "OK": st.success(f"{wc_display} ({wc_status})")
            elif "Exceeded" in wc_status: st.warning(f"{wc_display} ({wc_status})")
            else: st.error(f"{wc_display} ({wc_status})")
            # Required Sections
            missing = format_results['required_sections_missing']; found = format_results['required_sections_found']
            if not missing: st.success(f"Required Sections: All found ({', '.join(found)})")
            else:
                st.warning(f"Required Sections Missing: {', '.join(missing)}")
                if found: st.info(f"Sections Found: {', '.join(found)}")
# --- End of Streamlit App UI ---
# ==============================================================================
# == END OF mvp_app.py CODE ==
# ==============================================================================

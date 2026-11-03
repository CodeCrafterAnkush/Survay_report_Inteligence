import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(
    page_title="Survey Report Generator",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Survey Report Generator")
st.write(
    "Upload a CSV file containing survey responses. "
    "The app classifies feedback as Positive, Negative, or Neutral "
    "and creates visual reports."
)

# -----------------------------
# Sentiment keyword dictionaries
# -----------------------------
POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "awesome", "love", "loved",
    "like", "liked", "happy", "satisfied", "helpful", "useful", "best",
    "fantastic", "wonderful", "perfect", "recommend", "easy", "fast",
    "friendly", "smooth", "reliable", "impressed", "enjoyed", "positive"
}

NEGATIVE_WORDS = {
    "bad", "poor", "terrible", "awful", "worst", "hate", "hated",
    "dislike", "disliked", "unhappy", "dissatisfied", "unhelpful",
    "useless", "slow", "difficult", "confusing", "broken", "problem",
    "issue", "error", "delay", "delayed", "expensive", "rude",
    "disappointed", "disappointing", "negative", "frustrating"
}

NEGATION_WORDS = {"not", "no", "never", "cannot", "can't", "didn't", "don't", "doesn't", "wasn't", "isn't"}

def classify_text(text: str) -> str:
    """Classify a survey response as Positive, Negative, or Neutral."""
    if pd.isna(text) or str(text).strip() == "":
        return "Neutral"

    text = str(text).lower()
    words = re.findall(r"[a-z']+", text)

    positive_score = 0
    negative_score = 0

    for i, word in enumerate(words):
        if word in POSITIVE_WORDS:
            # Check simple negation, e.g. "not good"
            if i > 0 and words[i - 1] in NEGATION_WORDS:
                negative_score += 1
            else:
                positive_score += 1

        elif word in NEGATIVE_WORDS:
            # Check negated negative, e.g. "not bad"
            if i > 0 and words[i - 1] in NEGATION_WORDS:
                positive_score += 1
            else:
                negative_score += 1

    if positive_score > negative_score:
        return "Positive"
    elif negative_score > positive_score:
        return "Negative"
    else:
        return "Neutral"


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Upload & Settings")

uploaded_file = st.sidebar.file_uploader(
    "Upload survey CSV file",
    type=["csv"]
)

st.sidebar.info(
    "Your CSV should include a column with survey feedback, "
    "for example: `feedback`, `response`, `comment`, or `review`."
)

# -----------------------------
# Main app
# -----------------------------
if uploaded_file is None:
    st.warning("Please upload a CSV file to generate the survey report.")

    st.subheader("Expected CSV format")
    st.code(
        """response_id,feedback
1,The service was excellent and very helpful.
2,I did not like the delay in delivery.
3,The product is okay but packaging could improve.""",
        language="csv"
    )

else:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read the CSV file: {e}")
        st.stop()

    if df.empty:
        st.error("The uploaded CSV file is empty.")
        st.stop()

    st.success(f"Successfully loaded **{len(df)}** survey responses.")

    # Identify feedback column
    possible_columns = [
        c for c in df.columns
        if df[c].dtype == object
        and any(keyword in c.lower() for keyword in
                ["feedback", "response", "comment", "review", "survey", "opinion", "text"])
    ]

    with st.sidebar:
        feedback_column = st.selectbox(
            "Select the survey feedback column",
            options=df.columns.tolist(),
            index=df.columns.get_loc(possible_columns[0]) if possible_columns else 0
        )

    # Classify responses
    df["Sentiment"] = df[feedback_column].apply(classify_text)

    # Summary metrics
    sentiment_counts = df["Sentiment"].value_counts()
    total = len(df)

    positive_count = int(sentiment_counts.get("Positive", 0))
    negative_count = int(sentiment_counts.get("Negative", 0))
    neutral_count = int(sentiment_counts.get("Neutral", 0))

    st.subheader("📈 Survey Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Responses", total)
    col2.metric("Positive", positive_count, f"{positive_count / total:.1%}")
    col3.metric("Negative", negative_count, f"{negative_count / total:.1%}")
    col4.metric("Neutral", neutral_count, f"{neutral_count / total:.1%}")

    # -----------------------------
    # Pie chart: overall sentiment
    # -----------------------------
    st.subheader("🥧 Overall Sentiment Distribution")

    pie_data = pd.DataFrame({
        "Sentiment": ["Positive", "Negative", "Neutral"],
        "Count": [positive_count, negative_count, neutral_count]
    })

    pie_data = pie_data[pie_data["Count"] > 0]

    if pie_data.empty:
        st.info("No sentiment data available to plot.")
    else:
        color_map = {
            "Positive": "#2ecc71",
            "Negative": "#e74c3c",
            "Neutral": "#95a5a6"
        }

        fig_pie = px.pie(
            pie_data,
            names="Sentiment",
            values="Count",
            title="Survey Responses by Sentiment",
            color="Sentiment",
            color_discrete_map=color_map,
            hole=0.45
        )

        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    # -----------------------------
    # Bar graph: sentiment counts
    # -----------------------------
    st.subheader("📊 Sentiment Count Graph")

    fig_bar = px.bar(
        pie_data,
        x="Sentiment",
        y="Count",
        color="Sentiment",
        title="Number of Positive, Negative, and Neutral Responses",
        color_discrete_map=color_map,
        text="Count"
    )

    fig_bar.update_layout(
        xaxis_title="Sentiment Type",
        yaxis_title="Number of Responses",
        showlegend=False
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    # -----------------------------
    # Optional category-wise analysis
    # -----------------------------
    categorical_columns = df.select_dtypes(include=["object", "category"]).columns.tolist()
    categorical_columns = [c for c in categorical_columns if c != feedback_column and c != "Sentiment"]

    if categorical_columns:
        st.subheader("🗂️ Category-wise Sentiment Analysis")

        category_column = st.selectbox(
            "Select a category column",
            options=["None"] + categorical_columns
        )

        if category_column != "None":
            category_sentiment = (
                df.groupby([category_column, "Sentiment"])
                .size()
                .reset_index(name="Count")
            )

            fig_category = px.bar(
                category_sentiment,
                x=category_column,
                y="Count",
                color="Sentiment",
                barmode="group",
                title=f"Sentiment by {category_column}",
                color_discrete_map=color_map
            )

            st.plotly_chart(fig_category, use_container_width=True)

            category_pie = px.pie(
                category_sentiment,
                names="Sentiment",
                values="Count",
                facet_col=category_column,
                title=f"Sentiment Proportion by {category_column}",
                color="Sentiment",
                color_discrete_map=color_map
            )

            st.plotly_chart(category_pie, use_container_width=True)

    # -----------------------------
    # Classified report table
    # -----------------------------
    st.subheader("📋 Classified Survey Report")

    sentiment_filter = st.multiselect(
        "Filter by sentiment",
        options=["Positive", "Negative", "Neutral"],
        default=["Positive", "Negative", "Neutral"]
    )

    filtered_df = df[df["Sentiment"].isin(sentiment_filter)]

    st.dataframe(filtered_df, use_container_width=True)

    # Download report
    csv_report = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download classified survey report",
        data=csv_report,
        file_name="classified_survey_report.csv",
        mime="text/csv"
    )
    
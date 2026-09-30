import os

import httpx
import streamlit as st


st.title("Ticket Intelligence")
question = st.text_input("Question")

if st.button("Ask"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        api_url = os.getenv("STREAMLIT_API_URL", "http://localhost:8000/query")
        try:
            response = httpx.post(api_url, json={"question": question}, timeout=60)
            response.raise_for_status()
            result = response.json()
            if result.get("error"):
                st.error(result["error"])
            elif result.get("intent") == "data_query" and result.get("rows") is not None:
                if result["rows"]:
                    st.dataframe(result["rows"], use_container_width=True)
                else:
                    st.info("No rows returned.")
                if result.get("sql"):
                    with st.expander("SQL used"):
                        st.code(result["sql"], language="sql")
                if result.get("assumptions"):
                    st.markdown("\n".join(f"- {item}" for item in result["assumptions"]))
            elif result.get("intent") == "anomaly_query" and result.get("anomalies") is not None:
                for item in result["anomalies"]:
                    st.write(f"**{item['ticket_id']}** {item['reason']}")
            elif result.get("intent") == "unsupported":
                st.info(result.get("message", ""))
        except (httpx.HTTPError, ValueError) as exc:
            st.error(f"API request failed: {exc}")
import streamlit as st
import psycopg2
import pandas as pd

# ------------------------ DB Connection ------------------------
def get_connection():
    return psycopg2.connect(
        host='localhost',
        database='food_waste',
        user='postgres',
        password='POSTGRESQL'  # 🔁 Change this if your password is different
    )

# ------------------------ Sidebar ------------------------
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to:", [
    "🏠 Project Introduction",
    "📄 View Tables",
    "🛠️ CRUD Operations",
    "📊 SQL Analysis",
    "🧠 Custom SQL",
    "👤 About Creator"
])

# ------------------------ Page 1: Introduction ------------------------
if page == "🏠 Project Introduction":
   
    st.title("🌍 Local Food Wastage Management System")

    st.markdown("""
    ### Problem Statement:
    * Food wastage is a significant issue, with many households and restaurants discarding surplus food.
    * At the same time, numerous people struggle with food insecurity.

    ### Project Aim:
    * Providers: Restaurants, households, and businesses list surplus food.
    * Receivers: NGOs and individuals claim the available food.
    * Behavior Analysis: Track the usage habits of food providers and receivers.
    * SQL Analysis: Generate valuable insights using SQL queries.
    """)
    st.image("https://cdn-icons-png.flaticon.com/512/3075/3075977.png", width=400)

# ------------------------ Page 2: View Tables ------------------------
elif page == "📄 View Tables":
    st.title("📄 View Data Tables")
    table = st.selectbox("Choose a table to view", ["providers", "receivers", "food_listings", "claims"])
    
    try:
        conn = get_connection()
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        conn.close()

        if not df.empty:
            st.subheader(f"Data from '{table}' table")
            
            # --- Column Filters ---
            st.subheader("📊 Filter Data")
            
            # Get list of all columns
            all_columns = df.columns.tolist()
            
            # Allow user to select columns to filter
            columns_to_filter = st.multiselect("Select columns to apply filters", all_columns)
            
            filtered_df = df.copy() # Start with a copy to apply filters

            for col in columns_to_filter:
                col_type = filtered_df[col].dtype

                if pd.api.types.is_numeric_dtype(col_type):
                    min_val = float(filtered_df[col].min())
                    max_val = float(filtered_df[col].max())
                    
                    # Ensure min_val and max_val are distinct for slider to work correctly
                    if min_val == max_val:
                        st.info(f"Column '{col}' has only one unique numeric value: {min_val}. No range filter needed.")
                        continue

                    value_range = st.slider(
                        f"Filter '{col}' (numeric range)",
                        min_value=min_val,
                        max_value=max_val,
                        value=(min_val, max_val),
                        step=(max_val - min_val) / 100 if (max_val - min_val) > 0 else 0.1
                    )
                    filtered_df = filtered_df[
                        (filtered_df[col] >= value_range[0]) & 
                        (filtered_df[col] <= value_range[1])
                    ]
                
                elif pd.api.types.is_datetime64_any_dtype(col_type):
                    # Convert to datetime if not already
                    filtered_df[col] = pd.to_datetime(filtered_df[col], errors='coerce')
                    min_date = filtered_df[col].min().date() if not filtered_df[col].min() is pd.NaT else None
                    max_date = filtered_df[col].max().date() if not filtered_df[col].max() is pd.NaT else None

                    if min_date and max_date and min_date != max_date:
                        date_range = st.date_input(
                            f"Filter '{col}' (date range)",
                            value=(min_date, max_date),
                            min_value=min_date,
                            max_value=max_date
                        )
                        if len(date_range) == 2:
                            filtered_df = filtered_df[
                                (filtered_df[col].dt.date >= date_range[0]) & 
                                (filtered_df[col].dt.date <= date_range[1])
                            ]
                    elif min_date:
                        st.info(f"Column '{col}' has only one unique date value: {min_date}. No date range filter needed.")
                    else:
                        st.info(f"Column '{col}' has no valid date values for filtering.")

                else: # Treat as categorical (object, string)
                    unique_values = filtered_df[col].unique().tolist()
                    if len(unique_values) > 0:
                        selected_values = st.multiselect(f"Filter '{col}' (select values)", unique_values, default=unique_values)
                        filtered_df = filtered_df[filtered_df[col].isin(selected_values)]
                    else:
                        st.info(f"Column '{col}' has no unique values for filtering.")

            st.dataframe(filtered_df)
        else:
            st.info(f"No data available in the '{table}' table.")

    except Exception as e:
        st.error(f"Failed to load table or apply filters: {e}")


# ------------------------ Page 3: CRUD Operations ------------------------
elif page == "🛠️ CRUD Operations":
    st.title("🛠️ Perform CRUD Operations on Food Listings")

    crud_operation = st.selectbox("Choose a CRUD Operation", ["Add New Listing", "Update Existing Listing", "Delete Listing"])

    # ------------------------ Add New Listing ------------------------
    if crud_operation == "Add New Listing":
        st.subheader("➕ Add New Food Listing")
        with st.form("add_form"):
            name = st.text_input("Food Name")
            quantity = st.number_input("Quantity", min_value=1)
            expiry_date = st.date_input("Expiry Date")
            provider_id = st.number_input("Provider ID", min_value=1, format="%d")
            provider_type = st.text_input("Provider Type")
            location = st.text_input("Location")
            food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
            meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"])
            submit = st.form_submit_button("Add Listing")

            if submit:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO food_listings (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type))
                    conn.commit()
                    conn.close()
                    st.success("✅ Food listing added successfully!")
                except Exception as e:
                    st.error(f"❌ Error adding listing: {e}")

    # ------------------------ Update Existing Listing ------------------------
    elif crud_operation == "Update Existing Listing":
        st.subheader("✏️ Update Food Listing")
        
        try:
            conn = get_connection()
            food_listings_df = pd.read_sql("SELECT food_id, food_name FROM food_listings ORDER BY food_id", conn)
            conn.close()

            if not food_listings_df.empty:
                food_id_options = food_listings_df['food_id'].tolist()
                selected_food_id = st.selectbox("Select Food ID to Update", food_id_options)

                # Fetch details of the selected listing
                conn = get_connection()
                selected_listing_df = pd.read_sql(f"SELECT * FROM food_listings WHERE food_id = {selected_food_id}", conn)
                conn.close()

                if not selected_listing_df.empty:
                    listing_data = selected_listing_df.iloc[0]
                    
                    with st.form("update_form"):
                        new_name = st.text_input("Food Name", value=listing_data["food_name"])
                        new_quantity = st.number_input("Quantity", min_value=1, value=int(listing_data["quantity"]))
                        new_expiry_date = st.date_input("Expiry Date", value=listing_data["expiry_date"])
                        new_provider_id = st.number_input("Provider ID", min_value=1, value=int(listing_data["provider_id"]), format="%d")
                        new_provider_type = st.text_input("Provider Type", value=listing_data["provider_type"])
                        new_location = st.text_input("Location", value=listing_data["location"])
                        new_food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"], index=["Vegetarian", "Non-Vegetarian", "Vegan"].index(listing_data["food_type"]))
                        new_meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"], index=["Breakfast", "Lunch", "Dinner", "Snacks"].index(listing_data["meal_type"]))
                        
                        update_submit = st.form_submit_button("Update Listing")

                        if update_submit:
                            try:
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE food_listings
                                    SET Food_Name = %s, Quantity = %s, Expiry_Date = %s, Provider_ID = %s, 
                                        Provider_Type = %s, Location = %s, Food_Type = %s, Meal_Type = %s
                                    WHERE Food_ID = %s
                                """, (new_name, new_quantity, new_expiry_date, new_provider_id, 
                                      new_provider_type, new_location, new_food_type, new_meal_type, 
                                      selected_food_id))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ Food listing with ID {selected_food_id} updated successfully!")
                            except Exception as e:
                                st.error(f"❌ Error updating listing: {e}")
                else:
                    st.info("No data found for the selected Food ID.")
            else:
                st.info("No food listings available to update.")
        except Exception as e:
            st.error(f"❌ Error loading food listings for update: {e}")

    # ------------------------ Delete Listing ------------------------
    elif crud_operation == "Delete Listing":
        st.subheader("🗑️ Delete Food Listing")
        
        try:
            conn = get_connection()
            food_listings_df = pd.read_sql("SELECT food_id, food_name FROM food_listings ORDER BY food_id", conn)
            conn.close()

            if not food_listings_df.empty:
                food_id_options = food_listings_df['food_id'].tolist()
                selected_food_id_delete = st.selectbox("Select Food ID to Delete", food_id_options)

                delete_submit = st.button(f"Delete Listing with ID {selected_food_id_delete}")

                if delete_submit:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM food_listings WHERE Food_ID = %s", (selected_food_id_delete,))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Food listing with ID {selected_food_id_delete} deleted successfully!")
                    except Exception as e:
                        st.error(f"❌ Error deleting listing: {e}")
            else:
                st.info("No food listings available to delete.")
        except Exception as e:
            st.error(f"❌ Error loading food listings for deletion: {e}")

# ------------------------ Page 3: CRUD Operations (Add Only) ------------------------
elif page == "🛠️ CRUD Operations":
    st.title("➕ Add New Food Listing")

    with st.form("add_form"):
        name = st.text_input("Food Name")
        quantity = st.number_input("Quantity", min_value=1)
        expiry_date = st.date_input("Expiry Date")
        provider_id = st.number_input("Provider ID", min_value=1)
        provider_type = st.text_input("Provider Type")
        location = st.text_input("Location")
        food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"])
        submit = st.form_submit_button("Add Listing")

        if submit:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO food_listings (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type))
                conn.commit()
                conn.close()
                st.success("✅ Food listing added successfully!")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ------------------------ Page 4: SQL Analysis ------------------------
elif page == "📊 SQL Analysis":
    st.title("📈 SQL Insights") # Changed title slightly as no graphs are present

    # Define SQL queries based on the user's specific questions
    sql_queries = {
        "1. How many food providers and receivers are there in each city?": """
            SELECT
                COALESCE(p.city, r.city) AS city,
                COALESCE(p.num_providers, 0) AS num_providers,
                COALESCE(r.num_receivers, 0) AS num_receivers
            FROM
                (SELECT city, COUNT(*) AS num_providers FROM providers GROUP BY city) p
            FULL OUTER JOIN
                (SELECT city, COUNT(*) AS num_receivers FROM receivers GROUP BY city) r
            ON p.city = r.city
            ORDER BY city;
        """,
        "2. Which type of food provider (restaurant, grocery store, etc.) contributes the most food?": """
            SELECT
                provider_type,
                SUM(quantity) AS total_quantity
            FROM food_listings
            GROUP BY provider_type
            ORDER BY total_quantity DESC
            LIMIT 3;
        """,
        "3. What is the contact information of food providers in a specific city?": """
            SELECT
                name,
                type,
                contact
            FROM providers
            WHERE city = 'New Jessica';
        """,
        "4. Which receivers have claimed the most food?": """
            SELECT
                r.name AS receiver_name,
                COUNT(c.claim_id) AS total_claims
            FROM claims c
            JOIN receivers r ON c.receiver_id = r.receiver_id
            GROUP BY r.name
            ORDER BY total_claims DESC LIMIT 5;
        """,
        "5. What is the total quantity of food available from all providers?": """
            SELECT
                    SUM(quantity) AS total_food_quantity
            FROM food_listings;
            """,
        "6. Which city has the highest number of food listings?": """
            SELECT Location AS City, COUNT(*) AS Number_of_Listings
            FROM food_listings
            GROUP BY Location
            ORDER BY Number_of_Listings DESC
            LIMIT 1;
        """,
        "7. What are the most commonly available food types?": """
            SELECT Food_Type, COUNT(*) AS Count
            FROM food_listings
            GROUP BY Food_Type
            ORDER BY Count DESC
            LIMIT 3;
        """,
        "8. How many food claims have been made for each food item?": """
            SELECT f.Food_Name, COUNT(c.claim_id) AS Number_of_Claims
            FROM claims c
            JOIN food_listings f ON c.food_id = f.food_id
            GROUP BY f.Food_Name
            ORDER BY Number_of_Claims DESC;
        """,
        "9. Which provider has had the highest number of successful food claims?": """
            SELECT p.Name AS Provider_Name, COUNT(c.claim_id) AS Successful_Claims
            FROM claims c
            JOIN food_listings f ON c.food_id = f.food_id
            JOIN providers p ON f.provider_id = p.provider_id
            WHERE c.status = 'Completed'
            GROUP BY p.Name
            ORDER BY Successful_Claims DESC
            LIMIT 1;
        """,
        "10. What percentage of food claims are completed vs. pending vs. canceled?": """
            SELECT
                status,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM claims) AS percentage
            FROM claims
            GROUP BY status;
        """,
        "11. What is the average quantity of food claimed per receiver?": """
            SELECT
                r.name AS receiver_name,
                AVG(f.quantity) AS average_quantity_claimed
            FROM claims c
            JOIN food_listings f ON c.food_id = f.food_id
            JOIN receivers r ON c.receiver_id = r.receiver_id
            WHERE c.status = 'Completed'
            GROUP BY r.name
            ORDER BY average_quantity_claimed DESC;
        """,
        "12. Which meal type (breakfast, lunch, dinner, snacks) is claimed the most?": """
            SELECT f.Meal_Type, COUNT(c.claim_id) AS Claim_Count
            FROM claims c
            JOIN food_listings f ON c.food_id = f.food_id
            GROUP BY f.Meal_Type
            ORDER BY Claim_Count DESC
            LIMIT 1;
        """,
        "13. What is the total quantity of food donated by each provider?": """
            SELECT p.Name AS Provider_Name, SUM(f.Quantity) AS Total_Donated_Quantity
            FROM food_listings f
            JOIN providers p ON f.Provider_ID = p.Provider_ID
            GROUP BY p.Name
            ORDER BY Total_Donated_Quantity DESC;
        """
    }

    selected_query_question = st.selectbox("Select a SQL Analysis Query", list(sql_queries.keys()))

    if selected_query_question:
        query_to_execute = sql_queries[selected_query_question]
        # Remove number prefix for subheader display
        subheader_text = selected_query_question.split('. ', 1)[1] if '. ' in selected_query_question else selected_query_question
        st.subheader(f"Results for: {subheader_text}")
        try:
            conn = get_connection()
            df_result = pd.read_sql(query_to_execute, conn)
            if not df_result.empty:
                st.dataframe(df_result)
                # All chart generation code has been removed from this page.
            else:
                st.info("No results found for this query.")
            conn.close()
        except Exception as e:
            st.error(f"❌ Error executing query: {e}")
# ------------------------ Page 5: Custom SQL ------------------------
elif page == "🧠 Custom SQL":
    st.title("Custom SQL Queries with Visualizations")

    custom_sql_queries_with_visuals = {
        "1. Which food types are listed the most but rarely claimed?": {
            "query": """
                SELECT
                    f.Food_Type,
                    COUNT(DISTINCT f.Food_ID) AS total_listings,
                    COUNT(DISTINCT c.Claim_ID) AS total_claims,
                    ROUND(100.0 * COUNT(DISTINCT c.Claim_ID) / COUNT(DISTINCT f.Food_ID), 2) AS claim_rate
                FROM food_listings f
                LEFT JOIN claims c ON f.Food_ID = c.Food_ID
                GROUP BY f.Food_Type
                ORDER BY claim_rate ASC;
            """,
            "plot_type": "bar",
            "x_col": "food_type",
            "y_col": "claim_rate",
            "title": "Claim Rate by Food Type"
        },
        "2. Which providers have the most unclaimed food (by quantity)?": {
            "query": """
                SELECT
                    p.Name AS Provider_Name,
                    SUM(fl.Quantity) AS Total_Unclaimed_Quantity
                FROM food_listings fl
                JOIN providers p ON fl.Provider_ID = p.Provider_ID
                WHERE fl.Food_ID NOT IN (SELECT food_id FROM claims WHERE status = 'Completed')
                GROUP BY p.Name
                ORDER BY Total_Unclaimed_Quantity DESC;
            """,
            "plot_type": "bar",
            "x_col": "provider_name",
            "y_col": "total_unclaimed_quantity",
            "title": "Unclaimed Food Quantity by Provider"
        },
        "3. Which day of the week has the most unclaimed food (by quantity)?": {
            "query": """
                SELECT
                    TO_CHAR(f.Expiry_Date, 'Day') AS Day_Of_Week,
                    SUM(f.Quantity) AS Unclaimed_Quantity
                FROM food_listings f
                LEFT JOIN claims c ON f.Food_ID = c.Food_ID
                WHERE c.Claim_ID IS NULL OR c.Status != 'Completed'
                GROUP BY Day_Of_Week
                ORDER BY Unclaimed_Quantity DESC;
            """,
            "plot_type": "bar",
            "x_col": "day_of_week",
            "y_col": "unclaimed_quantity",
            "title": "Unclaimed Food Quantity by Day of Week"
        },
        "4. Which cities have the most unclaimed food listings?": {
            "query": """
                SELECT
                    fl.Location AS City,
                    COUNT(DISTINCT fl.Food_ID) AS Total_Listings,
                    COUNT(DISTINCT c.Claim_ID) AS Claimed_Listings,
                    COUNT(DISTINCT fl.Food_ID) - COUNT(DISTINCT c.Claim_ID) AS Unclaimed_Listings
                FROM food_listings fl
                LEFT JOIN claims c ON fl.Food_ID = c.Food_ID
                GROUP BY fl.Location
                ORDER BY Unclaimed_Listings DESC
                LIMIT 5;
            """,
            "plot_type": "bar",
            "x_col": "city",
            "y_col": "unclaimed_listings",
            "title": "Top 5 Cities by Unclaimed Food Listings"
        },
        "5. How many claims were made for food items after their expiry date?": {
            "query": """
                SELECT
                    COUNT(c.Claim_ID) AS Late_Claims
                FROM claims c
                JOIN food_listings f ON c.Food_ID = f.Food_ID
                WHERE c.Timestamp > f.Expiry_Date;
            """,
            "plot_type": "metric",
            "title": "Number of Late Claims (After Expiry)"
        },
        "6. Which provider type lists the most food overall (by quantity)?": {
            "query": """
                SELECT
                    provider_type,
                    SUM(quantity) AS total_quantity
                FROM food_listings
                GROUP BY provider_type
                ORDER BY total_quantity DESC
                LIMIT 3;
            """,
            "plot_type": "bar",
            "x_col": "provider_type",
            "y_col": "total_quantity",
            "title": "Top 3 Provider Types by Total Food Quantity Listed"
        },
        "7. Which receiver city receives the most total claimed quantity?": {
            "query": """
                SELECT
                    r.City,
                    SUM(f.Quantity) AS Total_Claimed_Quantity
                FROM claims c
                JOIN food_listings f ON c.Food_ID = f.Food_ID
                JOIN receivers r ON c.Receiver_ID = r.Receiver_ID
                WHERE c.Status = 'Completed'
                GROUP BY r.City
                ORDER BY Total_Claimed_Quantity DESC
                LIMIT 10;
            """,
            "plot_type": "bar",
            "x_col": "city",
            "y_col": "total_claimed_quantity",
            "title": "Top 10 Receiver Cities by Total Claimed Quantity"
        },
        "8. Which meal type has the most unclaimed food (by quantity)?": {
            "query": """
                SELECT
                    f.Meal_Type,
                    SUM(f.Quantity) - COALESCE(SUM(CASE WHEN c.Status = 'Completed' THEN f.Quantity ELSE 0 END), 0) AS Unclaimed_Quantity
                FROM food_listings f
                LEFT JOIN claims c ON f.Food_ID = c.Food_ID
                GROUP BY f.Meal_Type
                ORDER BY Unclaimed_Quantity DESC;
            """,
            "plot_type": "bar",
            "x_col": "meal_type",
            "y_col": "unclaimed_quantity",
            "title": "Unclaimed Food Quantity by Meal Type"
        },
        "9. Which specific food items are most frequently unclaimed?": {
            "query": """
                SELECT
                    f.Food_Name,
                    COUNT(DISTINCT f.Food_ID) AS Unclaimed_Listings
                FROM food_listings f
                LEFT JOIN claims c ON f.Food_ID = c.Food_ID
                WHERE c.Claim_ID IS NULL OR c.Status != 'Completed'
                GROUP BY f.Food_Name
                ORDER BY Unclaimed_Listings DESC
                LIMIT 10;
            """,
            "plot_type": "bar",
            "x_col": "food_name",
            "y_col": "unclaimed_listings",
            "title": "Top 10 Most Frequently Unclaimed Food Items"
        },
        "10. Which providers list the most food items that end up unclaimed?": {
            "query": """
                SELECT
                    p.Name AS Provider_Name,
                    COUNT(DISTINCT f.Food_ID) AS total_listings,
                    COUNT(DISTINCT c.Claim_ID) AS total_claims,
                    COUNT(DISTINCT f.Food_ID) - COUNT(DISTINCT c.Claim_ID) AS unclaimed_listings
                FROM providers p
                JOIN food_listings f ON p.Provider_ID = f.Provider_ID
                LEFT JOIN claims c ON f.Food_ID = c.Food_ID
                GROUP BY p.Name
                ORDER BY unclaimed_listings DESC
                LIMIT 5;
            """,
            "plot_type": "bar",
            "x_col": "provider_name",
            "y_col": "unclaimed_listings",
            "title": "Top 5 Providers by Unclaimed Food Listings"
        }
    }

    selected_custom_query_question = st.selectbox("Select a Custom SQL Query", list(custom_sql_queries_with_visuals.keys()))

    if selected_custom_query_question:
        query_info = custom_sql_queries_with_visuals[selected_custom_query_question]
        query_to_execute_custom = query_info["query"]
        plot_type = query_info["plot_type"]
        x_col = query_info.get("x_col")
        y_col = query_info.get("y_col")
        plot_title = query_info["title"]

        st.subheader(f"Results for: {selected_custom_query_question}")
        try:
            conn = get_connection()
            df_custom_result = pd.read_sql(query_to_execute_custom, conn)
            if not df_custom_result.empty:
                st.dataframe(df_custom_result)

                # Generate Visualization
                if plot_type == "bar" and x_col and y_col:
                    # For st.bar_chart, set the x_col as index
                    plot_df = df_custom_result.set_index(x_col)
                    st.bar_chart(plot_df[[y_col]])
                    st.caption(plot_title) # Using caption for title
                elif plot_type == "metric":
                    if not df_custom_result.empty:
                        value = df_custom_result.iloc[0, 0]
                        st.metric(label=plot_title, value=value)
                    else:
                        st.info("No data for this metric.")

            else:
                st.info("No results found for this query.")
            conn.close()
        except Exception as e:
            st.error(f"❌ Error executing custom query: {e}")
# ------------------------ Page 6: Creator ------------------------
elif page == "👤 About Creator":
    st.title("👤 Project Created By")
    st.markdown("""
    - **Name:** Surya Prakash
    - **Subject:** Data Science
    - **Batch:** DS-C-WD-E-B68
    - **Tool:** Streamlit + PostgreSQL + Python
    - **Platform:** VS Code, Jupyter Notebook, and PostgreSQL
    - **Qualification:** MBA in Business Analytics and HR
    - **Work Experience:** 1 year in HR
    - **Location:** Chennai
    - **GitHub:** (https://github.com/git-hub123user/Local-Food-Wastage-Management-System.git) 
    """)




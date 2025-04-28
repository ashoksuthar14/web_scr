import streamlit as st
import pandas as pd
import csv
import os
import time
from datetime import datetime
from utils.perplexity_api import get_info_from_perplexity
from utils.data_writer import write_to_csv, ensure_csv_structure, write_error_log, get_required_fields

st.set_page_config(page_title="Real Estate Data Collector", page_icon="🏙️", layout="wide")

def process_single_project(project_name, results_csv):
    """Process a single project and return the result"""
    try:
        with st.spinner(f"Fetching data for {project_name}..."):
            response = get_info_from_perplexity(project_name)
            
            # Check if there's error information
            has_error = "error" in response if isinstance(response, dict) else True
            
            if isinstance(response, dict):
                # Even with errors, we can still save the project info we have
                write_to_csv(response, results_csv)
                
                if has_error:
                    error_msg = response.get("error", "Unknown error")
                    write_error_log(project_name, error_msg)
                    return {"status": "partial", "message": error_msg, "data": response}
                else:
                    return {"status": "success", "data": response}
            else:
                # Not even a dict response
                error_msg = str(response)
                write_error_log(project_name, error_msg)
                
                # Create minimal data to save
                fallback_data = {
                    "Project Name": project_name,
                    "error": error_msg
                }
                # Fill in missing fields
                for key in get_required_fields():
                    if key not in fallback_data:
                        fallback_data[key] = "Information not available"
                        
                # Save what we can
                write_to_csv(fallback_data, results_csv)
                
                return {"status": "error", "message": error_msg, "data": fallback_data}
    except Exception as e:
        # Handle unexpected exceptions
        error_msg = str(e)
        write_error_log(project_name, error_msg)
        
        # Create minimal data to save
        fallback_data = {
            "Project Name": project_name,
            "error": error_msg
        }
        # Fill in missing fields
        for key in get_required_fields():
            if key not in fallback_data:
                fallback_data[key] = "Information not available"
                
        # Save what we can
        write_to_csv(fallback_data, results_csv)
        
        return {"status": "error", "message": error_msg, "data": fallback_data}

def process_project_list(project_names, results_csv):
    """Process a list of project names and show progress"""
    results = {"success": 0, "partial": 0, "failed": 0, "details": []}
    
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize the results file if it doesn't exist
    ensure_csv_structure(results_csv)
    
    total_projects = len(project_names)
    processed_projects = 0
    
    for i, project_name in enumerate(project_names):
        project_name = project_name.strip()
        if not project_name:  # Skip empty names
            continue
            
        # Update status
        status_text.text(f"Processing {i+1}/{total_projects}: {project_name}")
        
        # Process the project
        result = process_single_project(project_name, results_csv)
        processed_projects += 1
        
        # Update counters based on status
        if result["status"] == "success":
            results["success"] += 1
        elif result["status"] == "partial":
            results["partial"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "Project Name": project_name,
            "Status": result["status"],
            "Message": result.get("message", "Success")
        })
        
        # Update progress bar
        progress_bar.progress((i + 1) / total_projects)
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
    
    # Complete the progress
    progress_bar.progress(100)
    status_text.text(f"All projects processed! Success: {results['success']}, Partial: {results['partial']}, Failed: {results['failed']}")
    
    return results

def main():
    st.title("Real Estate Info Extractor 🏙️")
    
    # Create tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["Single Project", "Multiple Projects", "Upload CSV File"])
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Set the default filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"results_{timestamp}.csv"
    
    with st.sidebar:
        st.header("Output Settings")
        output_filename = st.text_input("Output Filename", value=default_filename)
        results_csv = os.path.join(output_dir, output_filename)
        
        # Options for error handling
        st.subheader("Processing Options")
        retry_count = st.slider("Max Retries for Failed Requests", 1, 5, 3)
        delay_between_projects = st.slider("Delay Between Projects (seconds)", 0, 10, 1)
        
        # View collected data
        if st.button("View Collected Data"):
            try:
                if os.path.exists(results_csv):
                    df = pd.read_csv(results_csv)
                    st.dataframe(df)
                else:
                    st.warning("No data collected yet.")
            except Exception as e:
                st.error(f"Error reading data: {e}")
        
        # View error log
        error_log = os.path.join(output_dir, "error_log.csv")
        if os.path.exists(error_log) and st.button("View Error Log"):
            try:
                df = pd.read_csv(error_log)
                st.dataframe(df)
            except Exception as e:
                st.error(f"Error reading error log: {e}")
    
    # Single Project Tab
    with tab1:
        project_name = st.text_input("Enter Project Name")
        
        if st.button("Get Project Info"):
            if not project_name:
                st.warning("Please enter a project name.")
            else:
                result = process_single_project(project_name, results_csv)
                
                if result["status"] == "success":
                    st.success(f"Data for '{project_name}' collected successfully!")
                    st.json(result["data"])
                elif result["status"] == "partial":
                    st.warning(f"Partial data collected with some errors: {result['message']}")
                    st.json(result["data"])
                else:
                    st.error(f"Failed to collect data: {result['message']}")
                    if "data" in result:
                        st.json(result["data"])
    
    # Multiple Projects Tab
    with tab2:
        project_names_text = st.text_area("Enter Project Names (one per line)")
        
        col1, col2 = st.columns(2)
        with col1:
            process_button = st.button("Process Multiple Projects")
        
        if process_button:
            if not project_names_text:
                st.warning("Please enter project names.")
            else:
                project_names = project_names_text.strip().split('\n')
                
                # Remove duplicates and empty lines
                project_names = [name.strip() for name in project_names if name.strip()]
                project_names = list(dict.fromkeys(project_names))  # Remove duplicates while preserving order
                
                st.info(f"Processing {len(project_names)} unique projects...")
                
                results = process_project_list(project_names, results_csv)
                
                st.success(f"Completed! Success: {results['success']}, Partial: {results['partial']}, Failed: {results['failed']}")
                
                # Offer download buttons
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="Download Results CSV",
                        data=open(results_csv, 'rb').read(),
                        file_name=output_filename,
                        mime="text/csv"
                    )
                
                with col2:
                    error_log = os.path.join(output_dir, "error_log.csv")
                    if os.path.exists(error_log):
                        st.download_button(
                            label="Download Error Log",
                            data=open(error_log, 'rb').read(),
                            file_name="error_log.csv",
                            mime="text/csv"
                        )
                
                # Display summary table
                st.subheader("Processing Results")
                df = pd.DataFrame(results["details"])
                st.dataframe(df)
    
    # CSV Upload Tab
    with tab3:
        uploaded_file = st.file_uploader("Upload CSV with Project Names", type=['csv'])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                # Check if the required column exists
                if "Project Name" in df.columns:
                    project_names = df["Project Name"].dropna().tolist()
                    
                    # Remove duplicates
                    project_names = [name.strip() for name in project_names if isinstance(name, str) and name.strip()]
                    project_names = list(dict.fromkeys(project_names))
                    
                    st.info(f"Found {len(project_names)} unique project names in CSV.")
                    
                    if st.button("Process CSV Projects"):
                        results = process_project_list(project_names, results_csv)
                        
                        st.success(f"Completed! Success: {results['success']}, Partial: {results['partial']}, Failed: {results['failed']}")
                        
                        # Offer download buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="Download Results CSV",
                                data=open(results_csv, 'rb').read(),
                                file_name=output_filename,
                                mime="text/csv"
                            )
                        
                        with col2:
                            error_log = os.path.join(output_dir, "error_log.csv")
                            if os.path.exists(error_log):
                                st.download_button(
                                    label="Download Error Log",
                                    data=open(error_log, 'rb').read(),
                                    file_name="error_log.csv",
                                    mime="text/csv"
                                )
                        
                        # Display summary table
                        st.subheader("Processing Results")
                        summary_df = pd.DataFrame(results["details"])
                        st.dataframe(summary_df)
                else:
                    st.error("CSV must contain a 'Project Name' column.")
            except Exception as e:
                st.error(f"Error processing CSV: {e}")

if __name__ == "__main__":
    main()
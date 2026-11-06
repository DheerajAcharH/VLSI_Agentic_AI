import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from google.api_core.exceptions import ResourceExhausted

# 1. API Configuration
genai.configure(api_key="Your_API_KEY")
model = genai.GenerativeModel('Your_AI_Model')

SYSTEM_RTL_PROMPT = """
You are an autonomous RTL generation agent.
CRITICAL INSTRUCTIONS:
1. Output ONLY valid synthesizable Verilog code inside ```verilog ``` code blocks.
2. Absolutely no conversational intro, greetings, or conclusions outside the code block.
"""

def verify_verilog(verilog_code, filename="fsm_module.v"):
    if "```verilog" in verilog_code:
        verilog_code = verilog_code.split("```verilog")[1].split("```")[0].strip()
    elif "```" in verilog_code:
        verilog_code = verilog_code.split("```")[1].split("```")[0].strip()
        
    with open(filename, "w") as f:
        f.write(verilog_code)
    
    iverilog_path = r"C:\iverilog\bin\iverilog.exe"
    cmd = [iverilog_path, "-t", "null", filename] if os.path.exists(iverilog_path) else ["iverilog", "-t", "null", filename]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            return True, "Compilation Successful! Code is clean.", verilog_code
        else:
            return False, result.stderr if result.stderr else result.stdout, verilog_code
    except FileNotFoundError:
        return False, "[CRITICAL ERROR] Compiler not found.", verilog_code

def explain_compiler_error(error_log, bad_code):
    prompt = f"Analyze this Icarus Verilog error concisely:\n- Exact Flaw:\n- Root Cause & Fix:\n\nLog:\n{error_log}\n\nCode:\n```verilog\n{bad_code}\n```"
    return model.generate_content(prompt).text

def explain_fsm(verilog_code):
    prompt = f"Break down this FSM:\n1. Total States\n2. Inputs/Outputs\n3. Scenario Walkthrough\n\nCode:\n```verilog\n{verilog_code}\n```"
    return model.generate_content(prompt).text

def generate_fsm_diagram(verilog_code):
    prompt = f"""
    Read this Verilog FSM and output ONLY a valid Graphviz DOT string to visualize it.
    - Nodes = States
    - Edges = Transitions, labeled with the exact input conditions.
    - DO NOT use markdown formatting. Output raw string starting with 'digraph G {{'
    
    Code:
    {verilog_code}
    """
    response = model.generate_content(prompt)
    dot_string = response.text
    if "```" in dot_string:
        dot_string = dot_string.split("```")[1].replace("dot", "").strip()
    return dot_string

def generate_testbench(verilog_code):
    prompt = f"""
    Write a complete Verilog testbench for the following module. 
    Include clock generation, reset sequencing, and stimulus covering all states.
    Output ONLY valid Verilog code inside a ```verilog ``` block.
    
    Code:
    {verilog_code}
    """
    response = model.generate_content(prompt)
    tb_code = response.text
    if "```verilog" in tb_code:
        tb_code = tb_code.split("```verilog")[1].split("```")[0].strip()
    elif "```" in tb_code:
        tb_code = tb_code.split("```")[1].split("```")[0].strip()
    return tb_code

# ==========================================
# STREAMLIT UI SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Veri-Agent | Autonomous RTL")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("⚙️ Agent Settings")
    max_attempts = st.slider("Max Auto-Debug Attempts", 1, 5, 3)
    fsm_style = st.selectbox("Architecture Style", ["3-Always Block (Moore/Mealy)", "2-Always Block"])
    st.markdown("---")
    st.caption("IEEE CEDA Hackathon Build")

st.title("Veri-Agent: FSM Architect & Debugger")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Design Specifications")
    
    # THE NEW TOGGLE SWITCH
    mode = st.radio("Operation Mode:", ["Synthesize from Scratch", "Debug Provided Code"], horizontal=True)
    
    user_prompt = st.text_area(
        "Enter Specifications or Paste Code to Debug:",
        height=250,
        value=f"WHO: Senior ASIC Design Engineer.\nWHAT: Synthesizable Verilog Vending Machine FSM.\nHOW:\n- Structure: {fsm_style}\n- 4 states: S_IDLE, S_WAIT_INPUT, S_DISPENSE_TEA, S_DISPENSE_COFFEE.\n- Inputs: clk, rst_n, coin_inserted, sel_tea, sel_coffee, completed.\n- Outputs: dispense_tea_out, dispense_coffee_out."
    )
    
    if st.button("Run Veri-Agent Pipeline", type="primary", use_container_width=True):
        with st.status("Agent Pipeline Running...", expanded=True) as status_box:
            attempt = 1
            
            # Reset UI states for a fresh run
            st.session_state['error_report'] = None 
            st.session_state['zero_errors'] = True
            if 'saved_dot' in st.session_state: del st.session_state['saved_dot']
            if 'saved_report' in st.session_state: del st.session_state['saved_report']
            if 'saved_tb' in st.session_state: del st.session_state['saved_tb']
            
            # SCENARIO B: FORCING THE ERROR FOR THE SABOTAGE DEMO
            if mode == "Debug Provided Code":
                status_box.write("**Initial Check:** Evaluating your provided code via Icarus Verilog...")
                success, error_log, clean_code = verify_verilog(user_prompt)
                
                if not success:
                    st.session_state['zero_errors'] = False
                    status_box.write("Error caught in provided code! Analyzing...")
                    try:
                        diagnosis = explain_compiler_error(error_log, user_prompt)
                    except ResourceExhausted:
                        diagnosis = "API Rate Limit Hit during diagnosis. Auto-retrying."
                        time.sleep(60)
                    
                    # Log the user's deliberate error into the UI
                    st.session_state['error_report'] = {'attempt': 'Initial Input', 'log': error_log, 'diagnosis': diagnosis}
                    status_box.write("Pausing 5s for API limits before self-correcting...")
                    time.sleep(5)
                    
                    # Feed the broken code and terminal error to the AI
                    prompt_to_send = f"{SYSTEM_RTL_PROMPT}\n\nThe provided code failed compilation with this error:\n{error_log}\n\nProblematic code:\n{user_prompt}\n\nFix the exact error and output the complete corrected module."
                else:
                    st.session_state['final_code'] = clean_code
                    status_box.update(label="Provided code is already clean! (0 Errors)", state="complete", expanded=False)
                    st.stop()
            
            # SCENARIO A: NORMAL SYNTHESIS
            else:
                prompt_to_send = f"{SYSTEM_RTL_PROMPT}\n\nTask:\n{user_prompt}"

            # --- AUTONOMOUS LOOP ---
            while attempt <= max_attempts:
                status_box.write(f"**Attempt {attempt}:** Generating candidate RTL...")
                
                try:
                    response = model.generate_content(prompt_to_send)
                except ResourceExhausted:
                    status_box.write("⚠️ API Rate Limit Hit! Pausing for 60 seconds to cool down...")
                    time.sleep(60)
                    continue
                
                status_box.write(f"**Attempt {attempt}:** Compiling via Icarus Verilog...")
                success, error_log, clean_code = verify_verilog(response.text)
                
                if success:
                    st.session_state['final_code'] = clean_code
                    if mode == "Debug Provided Code":
                        status_box.update(label="Bug successfully diagnosed and fixed!", state="complete", expanded=False)
                    else:
                        status_box.update(label=f"RTL Verified! (Took {attempt} attempts)", state="complete", expanded=False)
                    break
                else:
                    st.session_state['zero_errors'] = False
                    status_box.write(f"**Attempt {attempt} Failed:** Compiler caught syntax violation.")
                    
                    try:
                        diagnosis = explain_compiler_error(error_log, clean_code)
                    except ResourceExhausted:
                        diagnosis = "API Rate Limit Hit during diagnosis. Auto-retrying."
                        time.sleep(60)
                    
                    st.session_state['error_report'] = {'attempt': attempt, 'log': error_log, 'diagnosis': diagnosis}
                    
                    status_box.write("Pausing 5s for API limits before correcting...")
                    time.sleep(5)
                    prompt_to_send = f"{SYSTEM_RTL_PROMPT}\n\nFailed with error:\n{error_log}\n\nCode:\n{clean_code}\n\nFix it."
                    attempt += 1

            if attempt > max_attempts:
                status_box.update(label="Max attempts reached.", state="error")

    # --- DEBUGGER REPORT ---
    if 'zero_errors' in st.session_state:
        st.markdown("---")
        st.subheader("🛠️ Debugger Report")
        if st.session_state['zero_errors']:
            st.success("✅ 0 Errors. The RTL code compiled perfectly on the first pass.")
        elif st.session_state['error_report']:
            report = st.session_state['error_report']
            st.error(f"❌ Error Resolved (Caught on Attempt {report['attempt']})")
            st.info(report['diagnosis'])
            with st.expander("Raw Verilog Error Log"):
                st.code(report['log'], language="text")

# --- INTERACTIVE WORKSPACE (RIGHT COLUMN) ---
with col2:
    if 'final_code' in st.session_state:
        tab1, tab2, tab3 = st.tabs(["📝 Interactive Editor", "🔀 Flowchart & Testbench", "📊 Architecture Report"])
        
        # TAB 1: Editor & Downloads
        with tab1:
            st.markdown("Edit the generated code manually and re-verify.")
            edited_code = st.text_area("Verilog Code", value=st.session_state['final_code'], height=400, label_visibility="collapsed")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("Verify Manual Edits", use_container_width=True):
                    success, msg, _ = verify_verilog(edited_code)
                    if success:
                        st.success("Manual edits compiled successfully!")
                        st.session_state['final_code'] = edited_code
                    else:
                        st.error(f"Manual edit failed:\n{msg}")
            with col_d2:
                st.download_button("📥 Download .v File", data=edited_code, file_name="fsm_module.v", use_container_width=True)

        # TAB 2: Visual Graphviz Diagram AND Testbench
        with tab2:
            st.markdown("Architectural visualization and automated validation stimulus.")
            if st.button("Generate Flowchart & Testbench", use_container_width=True):
                # 1. Flowchart Generation
                if 'saved_dot' not in st.session_state:
                    with st.spinner("Rendering FSM logic into visual nodes..."):
                        dot_code = generate_fsm_diagram(st.session_state['final_code'])
                        st.session_state['saved_dot'] = dot_code 
                try:
                    st.graphviz_chart(st.session_state['saved_dot'])
                except Exception:
                    st.error("Graphviz render failed. Ensure output is valid DOT format.")
                    st.code(st.session_state['saved_dot'])
                
                st.markdown("---")
                
                # 2. Testbench Generation
                st.subheader("Automated Testbench")
                if 'saved_tb' not in st.session_state:
                    with st.spinner("Writing validation stimulus..."):
                        tb_code = generate_testbench(st.session_state['final_code'])
                        st.session_state['saved_tb'] = tb_code
                
                st.code(st.session_state['saved_tb'], language="verilog")
                st.download_button("📥 Download Testbench", data=st.session_state['saved_tb'], file_name="tb_fsm.v", use_container_width=True)

        # TAB 3: Text Report
        with tab3:
            st.markdown("Detailed breakdown of I/O mapping and scenario routing.")
            if st.button("Generate Report", use_container_width=True):
                if 'saved_report' not in st.session_state:
                    with st.spinner("Analyzing parameters..."):
                        report = explain_fsm(st.session_state['final_code'])
                        st.session_state['saved_report'] = report
                
                st.markdown(st.session_state['saved_report'])
    else:
        st.info("👈 Enter specifications and synthesize RTL to unlock the workspace.")
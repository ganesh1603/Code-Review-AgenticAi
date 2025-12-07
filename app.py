"""
AI-Powered Code Review System - Streamlit Web Application
Interactive web interface for automated code analysis using CrewAI + Gemini
"""

import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import FileReadTool
from crewai.llm import LLM
from dotenv import load_dotenv
import tempfile
import time
from datetime import datetime
import os
os.environ["GOOGLE_API_KEY"] = st.session_state.api_key


# Page configuration
st.set_page_config(
    page_title="AI Code Review System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .agent-card {
        padding: 1rem;
        border-radius: 10px;
        background: #f0f2f6;
        margin: 0.5rem 0;
    }
    .metric-card {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Load environment variables
load_dotenv()

# Initialize session state
if "api_key" not in st.session_state:
    # langchain-google-genai uses GOOGLE_API_KEY by default
    st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "")

if "review_result" not in st.session_state:
    st.session_state.review_result = None

if "review_history" not in st.session_state:
    st.session_state.review_history = []

# Header
st.markdown(
    '<h1 class="main-header">🔍 AI Code Review System</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Powered by 5 Specialized AI Agents | CrewAI + Google Gemini</p>',
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    # API Key input
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help=(
            "Get your free API key from Google AI Studio: "
            "https://ai.google.dev/gemini-api/docs/api-key"
        ),
    )

    if api_key_input:
        st.session_state.api_key = api_key_input
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ Please enter your Gemini API key")

    st.divider()

    # Model selection (updated to 2.5 family)
    st.subheader("🤖 AI Model")
    model_option = st.selectbox(
        "Select Model",
        [
            "gemini-2.5-flash-lite",  # fast & cheap, great default
            "gemini-2.5-pro",         # deeper reasoning, slower
        ],
        help="Flash-Lite is faster and cheaper, Pro is more accurate",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Lower = more consistent, Higher = more creative",
    )

    st.divider()

    # Agent status
    st.subheader("🤖 AI Agents")
    st.markdown(
        """
    <div class="agent-card">
        <strong>1. Code Quality Analyst</strong><br>
        Analyzes bugs & best practices
    </div>
    <div class="agent-card">
        <strong>2. Security Auditor</strong><br>
        Finds vulnerabilities
    </div>
    <div class="agent-card">
        <strong>3. Performance Expert</strong><br>
        Optimizes efficiency
    </div>
    <div class="agent-card">
        <strong>4. Documentation Writer</strong><br>
        Reviews documentation
    </div>
    <div class="agent-card">
        <strong>5. Review Synthesizer</strong><br>
        Creates final report
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Statistics
    st.subheader("📊 Session Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Reviews Done", len(st.session_state.review_history))
    with col2:
        st.metric("Active Agents", "5")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(
    ["📝 Code Input", "🔍 Review Results", "📚 Examples", "ℹ️ About"]
)

# Tab 1: Code Input
with tab1:
    st.header("Submit Code for Review")

    input_method = st.radio(
        "Choose input method:",
        ["Upload File", "Paste Code", "Use Example Code"],
        horizontal=True,
    )

    code_content = None
    file_name = "uploaded_code"

    if input_method == "Upload File":
        uploaded_file = st.file_uploader(
            "Upload your code file",
            type=[
                "py",
                "js",
                "java",
                "cpp",
                "c",
                "go",
                "rb",
                "php",
                "ts",
                "jsx",
            ],
            help=(
                "Supported: Python, JavaScript, Java, C++, C, Go, Ruby, "
                "PHP, TypeScript, JSX"
            ),
        )

        if uploaded_file:
            code_content = uploaded_file.read().decode("utf-8")
            file_name = uploaded_file.name
            st.success(
                f"✅ Loaded: {file_name} ({len(code_content)} characters)"
            )

    elif input_method == "Paste Code":
        code_content = st.text_area(
            "Paste your code here",
            height=300,
            placeholder="# Paste your code here...\ndef example_function():\n    pass",
        )
        file_name = "pasted_code.py"

    else:  # Use Example Code
        example_choice = st.selectbox(
            "Select example:",
            ["Security Issues", "Performance Problems", "Documentation Issues"],
        )

        if example_choice == "Security Issues":
            code_content = """
def get_user_data(user_id):
    # SQL Injection vulnerability
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    return db.execute(query)

def login(username, password):
    # Hardcoded credentials
    if username == "admin" and password == "admin123":
        return True
    return False

API_KEY = "sk-1234567890abcdef"  # Exposed secret
"""
        elif example_choice == "Performance Problems":
            code_content = """
def calculate_total(items):
    # O(n*m) nested loop
    total = 0
    for item in items:
        for price in item['prices']:
            total = total + price
    return total

def process_data(data):
    # Inefficient iteration
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result

def find_duplicates(arr):
    # O(n²) algorithm
    duplicates = []
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j]:
                duplicates.append(arr[i])
    return duplicates
"""
        else:  # Documentation Issues
            code_content = """
def calc(a, b, c):
    x = a + b
    y = x * c
    z = y / 2
    return z

def process(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item)
    return result

class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process(self):
        return [x * 2 for x in self.data]
"""
        file_name = f"example_{example_choice.lower().replace(' ', '_')}.py"

    # Display code preview
    if code_content:
        with st.expander("📄 Code Preview", expanded=True):
            # Default to Python highlighting; still fine for demo
            st.code(code_content, language="python", line_numbers=True)

    # Review button
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        review_button = st.button(
            "🚀 Start AI Review",
            type="primary",
            use_container_width=True,
            disabled=not (code_content and st.session_state.api_key),
        )

    if not st.session_state.api_key:
        st.warning("⚠️ Please configure your Gemini API key in the sidebar")

    # Process review
    if review_button and code_content:
        with st.spinner("🔄 AI Agents are analyzing your code..."):
            try:
                # Initialize LLM
                llm = LLM(
                    model=model_option,
                    verbose=False,
                    temperature=temperature,
                    google_api_key=st.session_state.api_key,
                )

                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False
                ) as tmp_file:
                    tmp_file.write(code_content)
                    tmp_file_path = tmp_file.name

                # Initialize tools
                file_tool = FileReadTool()

                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Create agents
                status_text.text("🤖 Initializing AI agents...")
                progress_bar.progress(10)

                code_analyzer = Agent(
                    role="Senior Code Quality Analyst",
                    goal=(
                        "Analyze code for bugs, code smells, and potential "
                        f"issues in {tmp_file_path}"
                    ),
                    backstory=(
                        "You are a veteran software engineer with 20 years "
                        "of experience in code reviews. You have a keen eye "
                        "for spotting bugs, performance issues, and "
                        "violations of best practices."
                    ),
                    verbose=False,
                    allow_delegation=False,
                    tools=[file_tool],
                    llm=llm,
                )

                security_auditor = Agent(
                    role="Cybersecurity Expert",
                    goal=(
                        "Identify security vulnerabilities and risks in "
                        f"{tmp_file_path}"
                    ),
                    backstory=(
                        "You are a certified security researcher specializing "
                        "in OWASP Top 10 vulnerabilities. You've prevented "
                        "countless security breaches."
                    ),
                    verbose=False,
                    allow_delegation=False,
                    tools=[file_tool],
                    llm=llm,
                )

                performance_expert = Agent(
                    role="Performance Optimization Specialist",
                    goal=(
                        "Analyze code performance and suggest optimizations "
                        f"for {tmp_file_path}"
                    ),
                    backstory=(
                        "You are a performance engineer who has optimized "
                        "applications serving millions of users."
                    ),
                    verbose=False,
                    allow_delegation=False,
                    tools=[file_tool],
                    llm=llm,
                )

                documentation_writer = Agent(
                    role="Technical Documentation Expert",
                    goal=(
                        "Review and improve code documentation for "
                        f"{tmp_file_path}"
                    ),
                    backstory=(
                        "You are a technical writer who believes great code "
                        "tells a story."
                    ),
                    verbose=False,
                    allow_delegation=False,
                    tools=[file_tool],
                    llm=llm,
                )

                review_synthesizer = Agent(
                    role="Lead Code Reviewer",
                    goal=(
                        "Synthesize all reviews and create actionable "
                        "recommendations"
                    ),
                    backstory=(
                        "You are a tech lead who has mentored dozens of "
                        "developers."
                    ),
                    verbose=False,
                    allow_delegation=False,
                    llm=llm,
                )

                progress_bar.progress(20)

                # Create tasks
                status_text.text("📋 Creating analysis tasks...")

                analyze_task = Task(
                    description=f"""
Analyze {tmp_file_path} for:
1. Code quality issues (complexity, readability, maintainability)
2. Potential bugs and logic errors
3. Code smells (duplicated code, long functions, etc.)
4. Adherence to coding standards and best practices
5. Error handling and edge cases

Always read the file contents with the FileReadTool before analyzing.
Provide specific line numbers and examples for each issue found.
""",
                    expected_output=(
                        "Detailed code quality analysis with specific "
                        "issues and line numbers."
                    ),
                    agent=code_analyzer,
                )

                security_task = Task(
                    description=f"""
Perform security audit of {tmp_file_path}:
1. Check for OWASP Top 10 vulnerabilities
2. Identify authentication/authorization issues
3. Look for injection vulnerabilities (SQL, XSS, Command)
4. Review input validation and sanitization
5. Check for hardcoded secrets or sensitive data

Rate each vulnerability by severity (Critical/High/Medium/Low) and
reference relevant lines from the file.
""",
                    expected_output=(
                        "Security audit report with vulnerability severity "
                        "ratings."
                    ),
                    agent=security_auditor,
                    context=[analyze_task],
                )

                performance_task = Task(
                    description=f"""
Analyze performance of {tmp_file_path}:
1. Identify algorithmic inefficiencies (O(n²), nested loops)
2. Check database query optimization
3. Look for memory leaks or excessive memory usage
4. Review caching opportunities

Suggest specific optimizations with expected impact and point to the
relevant code lines.
""",
                    expected_output=(
                        "Performance analysis with optimization "
                        "recommendations."
                    ),
                    agent=performance_expert,
                    context=[analyze_task],
                )

                documentation_task = Task(
                    description=f"""
Review documentation quality of {tmp_file_path}:
1. Check for missing docstrings/comments
2. Assess clarity of existing documentation
3. Identify undocumented complex logic
4. Review function/method parameter descriptions

Provide examples of improved documentation for key functions.
""",
                    expected_output=(
                        "Documentation review with improvement suggestions."
                    ),
                    agent=documentation_writer,
                    context=[analyze_task],
                )

                synthesis_task = Task(
                    description="""
Create comprehensive code review report:
1. Summarize all findings from other agents
2. Prioritize issues by severity and impact
3. Provide clear, actionable recommendations
4. Estimate effort required for each fix
5. Calculate overall code quality score (1-10)

Format as a professional code review report with sections:
- Summary
- Critical Issues
- Major Issues
- Minor Issues
- Recommendations & Next Steps
""",
                    expected_output=(
                        "Complete code review report with prioritized "
                        "recommendations."
                    ),
                    agent=review_synthesizer,
                    context=[
                        analyze_task,
                        security_task,
                        performance_task,
                        documentation_task,
                    ],
                )

                progress_bar.progress(30)

                # Create and run crew
                status_text.text("🔍 Agent 1/5: Analyzing code quality...")
                progress_bar.progress(40)

                code_review_crew = Crew(
                    agents=[
                        code_analyzer,
                        security_auditor,
                        performance_expert,
                        documentation_writer,
                        review_synthesizer,
                    ],
                    tasks=[
                        analyze_task,
                        security_task,
                        performance_task,
                        documentation_task,
                        synthesis_task,
                    ],
                    process=Process.sequential,
                    verbose=False,
                )

                # Progress updates (UI only)
                status_text.text("🔒 Agent 2/5: Auditing security...")
                progress_bar.progress(55)
                time.sleep(1)

                status_text.text("⚡ Agent 3/5: Analyzing performance...")
                progress_bar.progress(70)
                time.sleep(1)

                status_text.text("📝 Agent 4/5: Reviewing documentation...")
                progress_bar.progress(85)
                time.sleep(1)

                status_text.text("📊 Agent 5/5: Synthesizing results...")
                progress_bar.progress(95)

                # Execute review
                result = code_review_crew.kickoff(
                    inputs={"code_file": tmp_file_path}
                )

                progress_bar.progress(100)
                status_text.text("✅ Review complete!")

                # Store result
                st.session_state.review_result = {
                    "content": str(result),
                    "file_name": file_name,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "code": code_content,
                    "model": model_option,
                    "temperature": temperature,
                }

                # Add to history
                st.session_state.review_history.append(
                    st.session_state.review_result
                )

                # Cleanup
                try:
                    os.unlink(tmp_file_path)
                except OSError:
                    pass

                time.sleep(1)
                st.success("✅ Code review completed successfully!")
                st.balloons()

                # Hint to user
                st.info(
                    "👉 Switch to the 'Review Results' tab to see the "
                    "detailed analysis"
                )

            except Exception as e:
                st.error(f"❌ Error during review: {str(e)}")
                st.info(
                    "💡 Tip: Make sure your API key is valid, the selected "
                    "model exists, and you have internet connectivity."
                )

# Tab 2: Review Results
with tab2:
    st.header("📊 Review Results")

    if st.session_state.review_result:
        result = st.session_state.review_result

        # Metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("File", result["file_name"])
        with col2:
            st.metric("Model", result["model"])
        with col3:
            st.metric("Temperature", result["temperature"])
        with col4:
            st.metric("Timestamp", result["timestamp"])

        st.divider()

        # Results display
        st.subheader("🔍 Detailed Analysis")
        st.markdown(result["content"])

        st.divider()

        # Download options
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Report (TXT)",
                data=result["content"],
                file_name=(
                    f"review_{result['file_name']}_"
                    f"{result['timestamp'].replace(':', '-')}.txt"
                ),
                mime="text/plain",
            )
        with col2:
            st.download_button(
                label="📥 Download Code (Source)",
                data=result["code"],
                file_name=result["file_name"],
                mime="text/plain",
            )

    else:
        st.info(
            "👈 Submit code for review in the 'Code Input' tab to see "
            "results here."
        )

        # Show example of what results look like
        with st.expander("📖 What to expect in the review"):
            st.markdown(
                """
            The AI review will provide:

            **1. Code Quality Analysis**
            - Complexity issues
            - Code smells
            - Best practice violations
            - Bug potential

            **2. Security Audit**
            - OWASP Top 10 vulnerabilities
            - Injection risks
            - Authentication issues
            - Hardcoded secrets

            **3. Performance Analysis**
            - Algorithm efficiency
            - Memory usage
            - Optimization opportunities

            **4. Documentation Review**
            - Missing docstrings
            - Comment quality
            - Code clarity

            **5. Comprehensive Summary**
            - Prioritized issues
            - Fix effort estimates
            - Overall quality score
            - Actionable roadmap
            """
            )

# Tab 3: Examples
with tab3:
    st.header("📚 Example Reviews")

    st.markdown("Here are some common code issues our AI agents can detect:")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("❌ Bad Code")
        st.code(
            """
# Security Issue: SQL Injection
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)

# Performance Issue: O(n²)
def find_dups(arr):
    dups = []
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j]:
                dups.append(arr[i])
    return dups

# Hardcoded Secret
API_KEY = "sk-abc123"
""",
            language="python",
        )

    with col2:
        st.subheader("✅ Good Code")
        st.code(
            """
# Fixed: Parameterized Query
def get_user(user_id):
    \"\"\"Fetch user by ID safely.\"\"\"
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,))

# Fixed: O(n) with set
def find_dups(arr):
    \"\"\"Find duplicates efficiently.\"\"\"
    seen = set()
    dups = set()
    for item in arr:
        if item in seen:
            dups.add(item)
        seen.add(item)
    return list(dups)

# Fixed: Environment Variable
API_KEY = os.getenv("API_KEY")
""",
            language="python",
        )

    st.divider()

    st.subheader("🎯 What Our AI Agents Check")

    cols = st.columns(3)

    with cols[0]:
        st.markdown(
            """
        **🔒 Security**
        - SQL Injection
        - XSS vulnerabilities
        - CSRF risks
        - Hardcoded secrets
        - Input validation
        """
        )

    with cols[1]:
        st.markdown(
            """
        **⚡ Performance**
        - Algorithm complexity
        - Nested loops
        - Memory leaks
        - Database queries
        - Caching opportunities
        """
        )

    with cols[2]:
        st.markdown(
            """
        **📝 Quality**
        - Code smells
        - Best practices
        - Documentation
        - Error handling
        - Code readability
        """
        )

# Tab 4: About
with tab4:
    st.header("ℹ️ About This Application")

    st.markdown(
        """
    ### 🤖 AI-Powered Code Review System

    This application uses **5 specialized AI agents** to perform comprehensive
    code reviews automatically. Each agent focuses on a specific aspect of
    code quality, working together to provide detailed analysis.

    #### 🎯 Key Features:
    - **Multi-Agent Architecture**: 5 specialized AI agents working in sequence
    - **Comprehensive Analysis**: Quality, security, performance, and documentation
    - **Instant Feedback**: Results typically within seconds to a couple of minutes
    - **Multiple Input Methods**: Upload files, paste code, or use examples
    - **Detailed Reports**: Actionable recommendations with line numbers

    #### 🔧 Technology Stack:
    - **Frontend**: Streamlit
    - **AI Framework**: CrewAI
    - **Language Model**: Google Gemini 2.5 family
    - **Programming**: Python 3.10+

    #### 📊 Business Impact:
    - **Time Savings**: Much faster than manual reviews
    - **Cost Effective**: Automated reviews at API cost only
    - **24/7 Availability**: Never sleeps, always consistent
    - **Security**: Catches vulnerabilities before production

    #### 🚀 Getting Started:
    1. Get your free Gemini API key from Google AI Studio
    2. Enter the API key in the sidebar
    3. Upload your code or use an example
    4. Click "Start AI Review"
    5. View detailed results in seconds!

    #### 🛡️ Privacy & Security:
    - Code is processed temporarily and not stored by this app
    - API key stored only in session memory
    - No data retention by default

    ---

    **Built with ❤️ using CrewAI and Google Gemini**

    *Version 1.1.0 | December 2025*
    """
    )

    # System status
    st.divider()
    st.subheader("🔌 System Status")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.session_state.api_key:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Not Connected")
    with col2:
        # Avoid referencing agent variables that may not exist yet
        st.info("🤖 5 Agents Ready")
    with col3:
        st.info(f"📊 {len(st.session_state.review_history)} Reviews Done")

# Footer
st.divider()
st.markdown(
    """
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>🔍 AI Code Review System | Powered by CrewAI + Google Gemini</p>
    <p>Made with Streamlit • Multi-Agent Architecture • Production Ready</p>
</div>
""",
    unsafe_allow_html=True,
)

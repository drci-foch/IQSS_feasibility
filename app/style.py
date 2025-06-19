custom_css =  """
    <style>
    :root {
        --primary-color: #047dc1;
        --secondary-color: #8bbc35;
        --dark-color: #044c7c;
        --light-color: #f8f9fa;
        --text-color: #333333;
    }
    
    /* Style général */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: var(--primary-color);
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: var(--dark-color);
    }
    .stButton>button {
        width: 100%;
        background-color: var(--primary-color);
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: var(--dark-color);
    }
    .result-container {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        border-left: 4px solid var(--secondary-color);
        background-color: rgba(139, 188, 53, 0.1);
    }
    .highlight {
        color: var(--secondary-color);
        font-weight: bold;
    }
    .card {
        border: 1px solid #e6e6e6;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-top: 3px solid var(--primary-color);
    }
    .info-box {
        background-color: rgba(4, 125, 193, 0.1);
        border-radius: 0.5rem;
        padding: 1rem;
        border-left: 4px solid var(--primary-color);
    }
    </style>
    """


# Resume Review - How It Works

## Overview
The Resume Review feature extracts text from uploaded documents and performs intelligent analysis comparing your resume against job descriptions.

## Process Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Upload Resume  │────▶│  Extract Text    │────▶│  Analyze Content│
│  (PDF/DOCX/TXT) │     │  (PDF/DOCX/TXT)  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌──────────────────┐            │
│  Show Results   │◀────│  Compare Resume  │◀───────────┘
│  (Score/Gaps)   │     │  vs Job Desc     │
└─────────────────┘     └──────────────────┘
```

## Step-by-Step

### 1. File Upload
**Supported Formats:**
- PDF (.pdf)
- Word (.docx, .doc)
- Text (.txt, .md, .rtf)

**Size Limit:** 10MB maximum

### 2. Text Extraction

#### PDF Files
```python
# Extracts text from each page
from PyPDF2 import PdfReader
for page in reader.pages:
    text = page.extract_text()
```

#### Word Documents (DOCX)
```python
# Extracts paragraphs from document
from docx import Document
doc = Document(file)
paragraphs = [para.text for para in doc.paragraphs]
```

#### Plain Text
Direct UTF-8 or Latin-1 decoding

### 3. Keyword Extraction from Job Description

The system extracts important keywords from the JD:

**Technical Skills:**
- Programming languages: `python`, `javascript`, `java`, `c++`, `go`, `rust`
- Frameworks: `react`, `angular`, `vue`, `node.js`, `django`, `flask`
- Cloud/Tools: `aws`, `azure`, `gcp`, `docker`, `kubernetes`, `jenkins`
- Databases: `sql`, `mysql`, `postgresql`, `mongodb`, `redis`
- ML/Data: `tensorflow`, `pytorch`, `pandas`, `numpy`, `spark`
- Methodologies: `agile`, `scrum`, `ci/cd`, `devops`, `sre`

**From Requirements Section:**
- Extracts bullet points under "Requirements", "Qualifications", "Skills Required"
- Parses key phrases like "Experience with X", "Knowledge of Y"

### 4. Resume Analysis

#### Section Detection
- **Experience:** Work history, achievements
- **Skills:** Technical skills section
- **Education:** Degrees, certifications
- **Summary/Objective:** Professional summary

#### Keyword Matching
Compares resume text against JD keywords:
```
JD Keywords: ["aws", "kubernetes", "docker", "python", "go"]
Resume Text: "Software engineer with Python and JavaScript experience..."

Found: ["python"]
Missing: ["aws", "kubernetes", "docker", "go"]
Coverage: 20%
```

#### Scoring
- **Overall Score:** Average of section scores
- **Experience:** Checks for quantifiable achievements, action verbs
- **Skills:** Counts number of skills listed
- **ATS Compatibility:** Checks for formatting issues

### 5. Results Display

```json
{
  "overall_score": 65,
  "missing_keywords": ["kubernetes", "docker", "aws"],
  "strengths": ["Strong Python experience", "Good projects section"],
  "improvements": ["Add AWS skills", "Include Kubernetes experience"],
  "ats_compatible": true
}
```

## Example

### Resume Text
```
Software Engineer with 5 years experience.
Proficient in Python, JavaScript, React, Node.js.
Built REST APIs and microservices.
Bachelor degree in Computer Science.
```

### Job Description
```
Looking for Senior DevOps Engineer with:
- AWS, Kubernetes, Docker experience
- Terraform and CI/CD knowledge
- Python and Go programming
- Cloud infrastructure expertise
```

### Analysis Results
```json
{
  "overall_score": 42,
  "missing_keywords": [
    "docker",
    "aws", 
    "kubernetes",
    "go",
    "terraform",
    "ci/cd"
  ],
  "found_keywords": ["python"],
  "coverage": "16.7%",
  "recommendations": [
    "Add AWS and cloud experience",
    "Include containerization skills (Docker/Kubernetes)",
    "Mention CI/CD tools you've used"
  ]
}
```

## API Endpoints

### Upload & Analyze
```bash
POST /resume/upload
Content-Type: multipart/form-data

file: <resume.pdf>
job_description: "Looking for..."
role_type: "software_engineer"
```

### Text Analysis
```bash
POST /resume/analyze
?resume_text=Software+engineer...
&job_description=Looking+for...
&role_type=software_engineer
```

## Key Features

✅ **Automatic Text Extraction** - PDF, DOCX, TXT support  
✅ **JD Keyword Extraction** - Identifies important skills from job posting  
✅ **Smart Comparison** - Matches resume content against JD requirements  
✅ **Gap Analysis** - Shows exactly what's missing  
✅ **ATS Compatibility** - Checks formatting issues  
✅ **Score Breakdown** - Section-by-section scoring  

## Limitations

- Basic keyword matching (not semantic/natural language understanding)
- PDF extraction may miss formatting/tables
- Does not verify accuracy of claims
- Limited to extracted text (not visual layout analysis)

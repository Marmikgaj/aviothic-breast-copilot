


## A V I O T H I C
Clinical AI Systems

## Breast Cancer Report Copilot
## Implementation Plan

## Prepared July 2026
## Version 1.0  •  Internal Working Draft

This document outlines the technical plan for an AI assistant that analyzes uploaded breast imaging and pathology
reports, builds a structured patient context, and supports grounded clinical follow-up conversation. The system is
designed to assist clinicians by organizing information and explaining findings — it does not replace clinical
judgment.

Table of Contents
-  Product Vision .............................................................................................................................. 3
-  System Workflow.......................................................................................................................... 3
-  Recommended Tech Stack ............................................................................................................ 4
-  Core Modules ............................................................................................................................... 4
-  Datasets ....................................................................................................................................... 4
-  LLM Capabilities ............................................................................................................................ 5
-  Development Phases .................................................................................................................... 5
-  Evaluation..................................................................................................................................... 6
-  Final Deliverables .......................................................................................................................... 6


## Aviothic Breast Cancer Report Copilot — Implementation Plan
Page 3 of 6
## 1.  Product Vision
What the copilot does for the clinician, end to end.
- Upload pathology, mammography, ultrasound, MRI, PET-CT, or discharge reports.
- Extract structured clinical entities: BI-RADS, TNM, tumor size, biomarkers, lymph nodes, and
recommendations.
- Create a patient-specific context memory.
- Allow radiologists to ask unlimited follow-up questions about the uploaded report.
- Retrieve trusted breast cancer knowledge when needed, via retrieval-augmented generation (RAG).
- Generate structured summaries and downloadable reports.

## 2.  System Workflow
The pipeline a report follows from upload to conversation.
## Step Stage
1 Upload PDF / image
2 OCR (if needed)
3 Text cleaning
4 Medical entity extraction
5 LLM reasoning
6 RAG retrieval
7 Patient context memory
8 Conversational AI
9 Structured summary & JSON output

## 3.  Recommended Tech Stack
Primary technology choices by function.
## Function Choice
## Language Python 3.11

## Aviothic Breast Cancer Report Copilot — Implementation Plan
Page 4 of 6
## Function Choice
Editor VS Code
Framework FastAPI
LLM Qwen 3 8B or Llama 3 8B
Fine-tuning Unsloth + PEFT (QLoRA)
Embeddings bge-large-en or BioClinicalBERT embeddings
Vector database ChromaDB
OCR Tesseract + PyMuPDF
PDF parsing pdfplumber / PyMuPDF
NER spaCy + custom medical rules
Inference vLLM
Experiment tracking Weights & Biases
## Container Docker
Deployment RunPod / Vast.ai

## 4.  Core Modules
The functional building blocks of the system.
- Document ingestion
- OCR pipeline
- Medical entity extraction
- Patient context builder
- Breast cancer knowledge base
- RAG engine
- Conversation engine
- Safety & citation layer
- Structured report generator

## 5.  Datasets
Data sources for training, fine-tuning, and evaluation.

## Aviothic Breast Cancer Report Copilot — Implementation Plan
Page 5 of 6
## • CBIS-DDSM
- VinDr-Mammo
- PubMed abstracts
- PubMed Central Open Access
- Breast cancer guidelines, where licensing permits use
- Synthetic instruction datasets created from public sources

-  LLM Capabilities
What the model is expected to do once integrated.
- Summarize reports
- Extract biomarkers
- Explain BI-RADS
- Explain staging
- Highlight missing information
- Answer follow-up questions using report context
- Compare two reports
- Explain findings in simple language
- Generate structured JSON

## 7.  Development Phases
Sequenced delivery plan from data to deployment.
## Phase Focus
Phase 1 Data ingestion and preprocessing
Phase 2 OCR and report parser
Phase 3 Entity extraction
Phase 4 Fine-tune oncology LLM
Phase 5 Build RAG
Phase 6 Build patient context memory
Phase 7 Conversational assistant
Phase 8 Evaluation and deployment


## Aviothic Breast Cancer Report Copilot — Implementation Plan
Page 6 of 6
## 8.  Evaluation
How quality, safety, and performance are measured before release.
- Extraction precision / recall
- Summary quality review
- Hallucination testing
## • Latency
- Clinical review with radiologists
- Regression testing

## 9.  Final Deliverables
What is handed over at the end of the engagement.
- Breast cancer report copilot
- Conversation interface
- Patient context engine
- RAG knowledge base
- Fine-tuned oncology assistant
- Technical documentation
- Deployment guide
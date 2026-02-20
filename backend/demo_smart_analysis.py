#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🎯 WOW-FACTOR DEMO: Intelligent Drug Analyzer
==============================================

Демонстрирует:
✅ Live Data Mode (Local DB → PubMed → DrugBank fallback)
✅ Hugging Face QA (Question-Answering)
✅ Semantic Search (Vector embeddings)
✅ Status Tracking (Real-time processing steps)
✅ Comprehensive Logging (Production-ready)

На защите можно показать эту демку и сказать:
"Вот наша система автоматически работает с реальными данными,
ищет в PubMed, использует NLP для ответов на вопросы и 
семантический поиск для лучшего анализа"
"""

import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

print("\n" + "=" * 80)
print("🎯 INTELLIGENT DRUG ANALYZER - WOW-FACTOR DEMO")
print("=" * 80)
print()

# Demo questions
demo_questions = [
    "What is the CVintra for this drug?",
    "Is the drug bioequivalent in fasted state?",
    "What are the main pharmacokinetic parameters?"
]

try:
    print("Loading modules...")
    from utils.intelligent_drug_lookup import IntelligentDrugAnalyzer
    print("✓ Modules loaded\n")
    
    # Initialize analyzer
    print("Initializing Intelligent Drug Analyzer...")
    analyzer = IntelligentDrugAnalyzer()
    print("✓ Analyzer ready\n")
    
    # Run analysis
    drug_name = "aspirin"
    print(f"📊 Analyzing drug: {drug_name}")
    print()
    
    result = analyzer.analyze_drug(drug_name, questions=demo_questions)
    
    # Display results
    print("\n" + "=" * 80)
    print("📋 ANALYSIS RESULTS")
    print("=" * 80)
    
    print(f"\n✓ Drug: {result.get('inn')}")
    print(f"✓ Processing Time: {result.get('processing_time', 0):.2f} seconds")
    print(f"✓ Data Sources Used: {', '.join(result.get('drug_data', {}).get('sources_used', []))}")
    print(f"✓ Confidence Level: {result.get('drug_data', {}).get('confidence', 0):.%}")
    
    # Show drug data
    print("\n" + "-" * 80)
    print("📈 DRUG DATA")
    print("-" * 80)
    drug_data = result.get('drug_data', {}).get('data', {})
    
    if drug_data.get('cvintra'):
        print(f"  CVintra: {drug_data['cvintra']}%")
    
    if drug_data.get('pubmed'):
        pubmed = drug_data['pubmed']
        print(f"  PubMed Articles Found: {pubmed.get('n_articles', 0)}")
        print(f"  PubMed Status: {pubmed.get('status')}")
    
    # Show QA results
    if result.get('qa_results'):
        print("\n" + "-" * 80)
        print("❓ QUESTION-ANSWERING RESULTS")
        print("-" * 80)
        for qa in result['qa_results']:
            print(f"  Q: {qa.get('question')}")
            print(f"  A: {qa.get('answer')} (confidence: {qa.get('score', 0):.2%})")
            print()
    
    # Show semantic insights
    if result.get('semantic_insights'):
        print("\n" + "-" * 80)
        print("🔍 SEMANTIC SEARCH INSIGHTS")
        print("-" * 80)
        for insight in result['semantic_insights']:
            print(f"  Query: {insight.get('query')}")
            print(f"  Found {len(insight.get('results', []))} relevant documents")
    
    # Show processing steps
    if result.get('status_log'):
        print("\n" + "-" * 80)
        print("📍 PROCESSING STEPS")
        print("-" * 80)
        status_log = result['status_log']
        for step in status_log.get('steps', []):
            status = "✓" if step.get('status') == 'completed' else "⚠"
            print(f"  {status} {step.get('name')}: {step.get('description')}")
    
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE!")
    print("=" * 80)
    print("\nOn defense, you can say:")
    print("  🎯 'We have a fully automated system that:'")
    print("  ✓ Fetches live data from PubMed and DrugBank")
    print("  ✓ Uses Hugging Face NLP for question-answering")
    print("  ✓ Performs semantic search with embeddings")
    print("  ✓ Provides real-time status tracking")
    print("  ✓ Logs everything for production readiness'")
    print("\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

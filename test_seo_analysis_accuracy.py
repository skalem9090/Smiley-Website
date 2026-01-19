"""
Property-Based Tests for SEO Analysis Accuracy

**Feature: advanced-editor-system, Property 14: SEO Analysis Accuracy**

For any content modification, the SEO analyzer should provide accurate real-time feedback
including readability scores, meta description validation, heading structure analysis,
and keyword suggestions.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import os


@pytest.fixture(scope='module')
def driver():
    """Create a Selenium WebDriver instance"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)
    
    yield driver
    
    driver.quit()


@pytest.fixture(scope='module')
def test_page(driver):
    """Create a test page with SEO analyzer"""
    seo_analyzer_path = os.path.join('static', 'js', 'advanced-editor', 'seo-analyzer.js')
    
    with open(seo_analyzer_path, 'r', encoding='utf-8') as f:
        seo_analyzer_js = f.read()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>SEO Analyzer Test</title>
    </head>
    <body>
        <div id="test-container"></div>
        
        <script>
        {seo_analyzer_js}
        </script>
        
        <script>
            window.testReady = true;
        </script>
    </body>
    </html>
    """
    
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_file = f.name
    
    try:
        driver.get(f'file://{os.path.abspath(temp_file)}')
        
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return window.testReady === true')
        )
        
        yield driver
    finally:
        os.unlink(temp_file)


class TestSEOAnalysisAccuracy:
    """
    Property-Based Tests for SEO Analysis Accuracy
    
    **Feature: advanced-editor-system, Property 14: SEO Analysis Accuracy**
    """
    
    @settings(max_examples=50, deadline=3000)
    @given(
        text=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?',
            min_size=100,
            max_size=500
        )
    )
    def test_readability_score_calculation(self, test_page, text):
        """
        Property: Readability analysis should provide accurate Flesch scores
        for any text input.
        
        **Validates: Requirement 8.1**
        """
        driver = test_page
        
        script = f"""
        const analyzer = new window.SEOAnalyzer();
        const analysis = analyzer.analyze({{ text: {repr(text)} }});
        
        return {{
            hasReadability: !!analysis.readability,
            hasFleschScore: typeof analysis.readability.fleschScore === 'number',
            hasGradeLevel: typeof analysis.readability.gradeLevel === 'number',
            hasWordCount: typeof analysis.readability.words === 'number',
            hasSentenceCount: typeof analysis.readability.sentences === 'number',
            hasDifficulty: !!analysis.readability.difficulty,
            scoreInRange: analysis.readability.score >= 0 && analysis.readability.score <= 100
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasReadability'], "Should have readability analysis"
        assert result['hasFleschScore'], "Should have Flesch score"
        assert result['hasGradeLevel'], "Should have grade level"
        assert result['hasWordCount'], "Should have word count"
        assert result['hasSentenceCount'], "Should have sentence count"
        assert result['hasDifficulty'], "Should have difficulty level"
        assert result['scoreInRange'], "Score should be between 0 and 100"
    
    @settings(max_examples=50, deadline=3000)
    @given(
        description=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?',
            min_size=0,
            max_size=300
        )
    )
    def test_meta_description_validation(self, test_page, description):
        """
        Property: Meta description analysis should validate length and provide
        accurate feedback.
        
        **Validates: Requirement 8.2**
        """
        driver = test_page
        
        script = f"""
        const analyzer = new window.SEOAnalyzer();
        const analysis = analyzer.analyze({{
            text: 'Sample content',
            metaDescription: {repr(description)}
        }});
        
        return {{
            hasMetaAnalysis: !!analysis.metaDescription,
            lengthMatches: analysis.metaDescription.length === {len(description)},
            hasOptimalFlag: typeof analysis.metaDescription.isOptimal === 'boolean',
            hasTooShortFlag: typeof analysis.metaDescription.isTooShort === 'boolean',
            hasTooLongFlag: typeof analysis.metaDescription.isTooLong === 'boolean',
            hasPreview: analysis.metaDescription.preview !== undefined,
            scoreInRange: analysis.metaDescription.score >= 0 && analysis.metaDescription.score <= 100
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasMetaAnalysis'], "Should have meta description analysis"
        assert result['lengthMatches'], "Length should match input"
        assert result['hasOptimalFlag'], "Should have optimal flag"
        assert result['hasTooShortFlag'], "Should have too short flag"
        assert result['hasTooLongFlag'], "Should have too long flag"
        assert result['hasPreview'], "Should have preview"
        assert result['scoreInRange'], "Score should be between 0 and 100"
    
    @settings(max_examples=30, deadline=3000)
    @given(
        heading_count=st.integers(min_value=0, max_value=10),
        has_h1=st.booleans()
    )
    def test_heading_structure_analysis(self, test_page, heading_count, has_h1):
        """
        Property: Heading analysis should correctly identify structure issues.
        
        **Validates: Requirement 8.3**
        """
        driver = test_page
        
        script = f"""
        const analyzer = new window.SEOAnalyzer();
        
        const blocks = [];
        if ({str(has_h1).lower()}) {{
            blocks.push({{
                type: 'heading',
                content: {{ text: 'Main Heading', data: {{ level: 1 }} }}
            }});
        }}
        
        for (let i = 0; i < {heading_count}; i++) {{
            blocks.push({{
                type: 'heading',
                content: {{ text: 'Heading ' + i, data: {{ level: 2 }} }}
            }});
        }}
        
        const analysis = analyzer.analyze({{ blocks: blocks, text: 'Sample text' }});
        
        return {{
            hasHeadingAnalysis: !!analysis.headings,
            countMatches: analysis.headings.count === blocks.length,
            h1FlagCorrect: analysis.headings.hasH1 === {str(has_h1).lower()},
            hasStructure: Array.isArray(analysis.headings.structure),
            scoreInRange: analysis.headings.score >= 0 && analysis.headings.score <= 100
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasHeadingAnalysis'], "Should have heading analysis"
        assert result['countMatches'], "Heading count should match"
        assert result['h1FlagCorrect'], "H1 flag should be correct"
        assert result['hasStructure'], "Should have structure array"
        assert result['scoreInRange'], "Score should be between 0 and 100"
    
    @settings(max_examples=30, deadline=3000)
    @given(
        text=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            min_size=100,
            max_size=300
        ),
        keyword=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz',
            min_size=3,
            max_size=15
        )
    )
    def test_keyword_analysis(self, test_page, text, keyword):
        """
        Property: Keyword analysis should calculate density and provide suggestions.
        
        **Validates: Requirement 8.4**
        """
        driver = test_page
        
        # Ensure keyword appears in text at least once
        text_with_keyword = f"{keyword} {text} {keyword}"
        
        script = f"""
        const analyzer = new window.SEOAnalyzer();
        const analysis = analyzer.analyze({{
            text: {repr(text_with_keyword)},
            focusKeyword: {repr(keyword)}
        }});
        
        return {{
            hasKeywordAnalysis: !!analysis.keywords,
            keywordMatches: analysis.keywords.focusKeyword === {repr(keyword)},
            hasCount: typeof analysis.keywords.keywordCount === 'number',
            hasDensity: typeof analysis.keywords.density === 'number',
            hasTopKeywords: Array.isArray(analysis.keywords.topKeywords),
            scoreInRange: analysis.keywords.score >= 0 && analysis.keywords.score <= 100,
            countIsPositive: analysis.keywords.keywordCount >= 2
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasKeywordAnalysis'], "Should have keyword analysis"
        assert result['keywordMatches'], "Keyword should match"
        assert result['hasCount'], "Should have keyword count"
        assert result['hasDensity'], "Should have density"
        assert result['hasTopKeywords'], "Should have top keywords"
        assert result['scoreInRange'], "Score should be between 0 and 100"
        assert result['countIsPositive'], "Keyword count should be at least 2"
    
    @settings(max_examples=30, deadline=3000)
    @given(
        image_count=st.integers(min_value=0, max_value=10),
        alt_text_ratio=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_image_alt_text_validation(self, test_page, image_count, alt_text_ratio):
        """
        Property: Image analysis should validate alt text coverage.
        
        **Validates: Requirement 8.5**
        """
        driver = test_page
        
        images_with_alt = int(image_count * alt_text_ratio)
        
        script = f"""
        const analyzer = new window.SEOAnalyzer();
        
        const blocks = [];
        for (let i = 0; i < {images_with_alt}; i++) {{
            blocks.push({{
                type: 'image',
                content: {{ data: {{ altText: 'Image ' + i }} }}
            }});
        }}
        for (let i = 0; i < {image_count - images_with_alt}; i++) {{
            blocks.push({{
                type: 'image',
                content: {{ data: {{}} }}
            }});
        }}
        
        const analysis = analyzer.analyze({{ blocks: blocks, text: 'Sample text' }});
        
        return {{
            hasImageAnalysis: !!analysis.images,
            totalMatches: analysis.images.totalImages === {image_count},
            withAltMatches: analysis.images.imagesWithAlt === {images_with_alt},
            missingAltCorrect: analysis.images.missingAlt === {image_count - images_with_alt},
            scoreInRange: analysis.images.score >= 0 && analysis.images.score <= 100
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasImageAnalysis'], "Should have image analysis"
        assert result['totalMatches'], "Total images should match"
        assert result['withAltMatches'], "Images with alt should match"
        assert result['missingAltCorrect'], "Missing alt count should be correct"
        assert result['scoreInRange'], "Score should be between 0 and 100"


class TestSEOAnalysisEdgeCases:
    """Edge case tests for SEO analysis"""
    
    def test_empty_content_analysis(self, test_page):
        """Test analysis with empty content"""
        driver = test_page
        
        script = """
        const analyzer = new window.SEOAnalyzer();
        const analysis = analyzer.analyze({ text: '' });
        
        return {
            hasAnalysis: !!analysis,
            hasOverallScore: typeof analysis.overallScore === 'number',
            hasRecommendations: Array.isArray(analysis.recommendations)
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasAnalysis'], "Should handle empty content"
        assert result['hasOverallScore'], "Should have overall score"
        assert result['hasRecommendations'], "Should have recommendations"
    
    def test_very_long_content_analysis(self, test_page):
        """Test analysis with very long content"""
        driver = test_page
        
        script = """
        const analyzer = new window.SEOAnalyzer();
        const longText = 'word '.repeat(5000);
        const analysis = analyzer.analyze({ text: longText });
        
        return {
            hasAnalysis: !!analysis,
            wordCountCorrect: analysis.contentLength.wordCount === 5000,
            scoreInRange: analysis.overallScore >= 0 && analysis.overallScore <= 100
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasAnalysis'], "Should handle long content"
        assert result['wordCountCorrect'], "Word count should be correct"
        assert result['scoreInRange'], "Score should be in range"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

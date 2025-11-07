from typing import List, Dict, Any, Optional
import re
from datetime import datetime

class CitationService:
    """Service for generating citations in different formats"""
    
    def format_apa(self, paper: Dict[str, Any]) -> str:
        """Format citation in APA style"""
        # Extract paper details
        authors = paper.get("authors", [])
        title = paper.get("title", "")
        year = paper.get("publication_date", "").split("-")[0] if paper.get("publication_date") else ""
        journal = paper.get("journal", "")
        volume = paper.get("volume", "")
        issue = paper.get("issue", "")
        pages = paper.get("pages", "")
        doi = paper.get("doi", "")
        
        # Format authors
        author_str = ""
        if authors:
            if len(authors) == 1:
                author_str = f"{authors[0].get('name', '')}"
            elif len(authors) == 2:
                author_str = f"{authors[0].get('name', '')} & {authors[1].get('name', '')}"
            else:
                author_str = f"{authors[0].get('name', '')}, et al."
        
        # Build citation
        citation = f"{author_str} ({year}). {title}. "
        
        if journal:
            citation += f"{journal}"
            
            if volume:
                citation += f", {volume}"
                
                if issue:
                    citation += f"({issue})"
            
            if pages:
                citation += f", {pages}"
        
        citation += "."
        
        if doi:
            citation += f" https://doi.org/{doi}"
        
        return citation
    
    def format_mla(self, paper: Dict[str, Any]) -> str:
        """Format citation in MLA style"""
        # Extract paper details
        authors = paper.get("authors", [])
        title = paper.get("title", "")
        year = paper.get("publication_date", "").split("-")[0] if paper.get("publication_date") else ""
        journal = paper.get("journal", "")
        volume = paper.get("volume", "")
        issue = paper.get("issue", "")
        pages = paper.get("pages", "")
        doi = paper.get("doi", "")
        
        # Format authors
        author_str = ""
        if authors:
            if len(authors) == 1:
                name_parts = authors[0].get('name', '').split()
                if len(name_parts) > 1:
                    last_name = name_parts[-1]
                    first_name = ' '.join(name_parts[:-1])
                    author_str = f"{last_name}, {first_name}"
                else:
                    author_str = authors[0].get('name', '')
            elif len(authors) == 2:
                name_parts1 = authors[0].get('name', '').split()
                if len(name_parts1) > 1:
                    last_name1 = name_parts1[-1]
                    first_name1 = ' '.join(name_parts1[:-1])
                    author1 = f"{last_name1}, {first_name1}"
                else:
                    author1 = authors[0].get('name', '')
                    
                author_str = f"{author1} and {authors[1].get('name', '')}"
            else:
                name_parts = authors[0].get('name', '').split()
                if len(name_parts) > 1:
                    last_name = name_parts[-1]
                    first_name = ' '.join(name_parts[:-1])
                    author_str = f"{last_name}, {first_name}, et al."
                else:
                    author_str = f"{authors[0].get('name', '')}, et al."
        
        # Build citation
        citation = f"{author_str}. \"{title}.\" "
        
        if journal:
            citation += f"{journal}"
            
            if volume:
                citation += f", vol. {volume}"
                
                if issue:
                    citation += f", no. {issue}"
            
            if year:
                citation += f", {year}"
            
            if pages:
                citation += f", pp. {pages}"
        
        citation += "."
        
        if doi:
            citation += f" DOI: {doi}"
        
        return citation
    
    def format_chicago(self, paper: Dict[str, Any]) -> str:
        """Format citation in Chicago style"""
        # Extract paper details
        authors = paper.get("authors", [])
        title = paper.get("title", "")
        year = paper.get("publication_date", "").split("-")[0] if paper.get("publication_date") else ""
        journal = paper.get("journal", "")
        volume = paper.get("volume", "")
        issue = paper.get("issue", "")
        pages = paper.get("pages", "")
        doi = paper.get("doi", "")
        
        # Format authors
        author_str = ""
        if authors:
            if len(authors) == 1:
                name_parts = authors[0].get('name', '').split()
                if len(name_parts) > 1:
                    last_name = name_parts[-1]
                    first_name = ' '.join(name_parts[:-1])
                    author_str = f"{last_name}, {first_name}"
                else:
                    author_str = authors[0].get('name', '')
            elif len(authors) <= 3:
                authors_formatted = []
                for i, author in enumerate(authors):
                    name_parts = author.get('name', '').split()
                    if len(name_parts) > 1:
                        if i == 0:
                            last_name = name_parts[-1]
                            first_name = ' '.join(name_parts[:-1])
                            authors_formatted.append(f"{last_name}, {first_name}")
                        else:
                            authors_formatted.append(author.get('name', ''))
                    else:
                        authors_formatted.append(author.get('name', ''))
                
                author_str = ", ".join(authors_formatted[:-1]) + ", and " + authors_formatted[-1]
            else:
                name_parts = authors[0].get('name', '').split()
                if len(name_parts) > 1:
                    last_name = name_parts[-1]
                    first_name = ' '.join(name_parts[:-1])
                    author_str = f"{last_name}, {first_name}, et al."
                else:
                    author_str = f"{authors[0].get('name', '')}, et al."
        
        # Build citation
        citation = f"{author_str}. \"{title}.\""
        
        if journal:
            citation += f" {journal}"
            
            if volume:
                citation += f" {volume}"
                
                if issue:
                    citation += f", no. {issue}"
            
            if year:
                citation += f" ({year})"
            
            if pages:
                citation += f": {pages}"
        
        citation += "."
        
        if doi:
            citation += f" https://doi.org/{doi}"
        
        return citation
    
    def format_bibtex(self, paper: Dict[str, Any]) -> str:
        """Format citation in BibTeX format"""
        # Extract paper details
        authors = paper.get("authors", [])
        title = paper.get("title", "")
        year = paper.get("publication_date", "").split("-")[0] if paper.get("publication_date") else ""
        journal = paper.get("journal", "")
        volume = paper.get("volume", "")
        issue = paper.get("issue", "")
        pages = paper.get("pages", "")
        doi = paper.get("doi", "")
        publisher = paper.get("publisher", "")
        
        # Generate citation key
        citation_key = ""
        if authors and year:
            first_author_last_name = authors[0].get('name', '').split()[-1]
            citation_key = f"{first_author_last_name.lower()}{year}"
        else:
            citation_key = f"paper{paper.get('id', '')}"
        
        # Format authors for BibTeX
        author_str = " and ".join([author.get('name', '') for author in authors])
        
        # Build BibTeX entry
        bibtex = f"@article{{{citation_key},\n"
        bibtex += f"  author = {{{author_str}}},\n"
        bibtex += f"  title = {{{title}}},\n"
        
        if journal:
            bibtex += f"  journal = {{{journal}}},\n"
        
        if year:
            bibtex += f"  year = {{{year}}},\n"
        
        if volume:
            bibtex += f"  volume = {{{volume}}},\n"
        
        if issue:
            bibtex += f"  number = {{{issue}}},\n"
        
        if pages:
            bibtex += f"  pages = {{{pages}}},\n"
        
        if publisher:
            bibtex += f"  publisher = {{{publisher}}},\n"
        
        if doi:
            bibtex += f"  doi = {{{doi}}},\n"
            bibtex += f"  url = {{https://doi.org/{doi}}},\n"
        
        # Remove trailing comma from last entry
        bibtex = bibtex.rstrip(",\n") + "\n"
        bibtex += "}"
        
        return bibtex
    
    def format_citation(self, paper: Dict[str, Any], style: str = "apa") -> str:
        """Format citation in the specified style"""
        style = style.lower()
        
        if style == "apa":
            return self.format_apa(paper)
        elif style == "mla":
            return self.format_mla(paper)
        elif style == "chicago":
            return self.format_chicago(paper)
        elif style == "bibtex":
            return self.format_bibtex(paper)
        else:
            return self.format_apa(paper)  # Default to APA
    
    def format_multiple_citations(self, papers: List[Dict[str, Any]], style: str = "apa") -> List[str]:
        """Format multiple citations in the specified style"""
        return [self.format_citation(paper, style) for paper in papers]
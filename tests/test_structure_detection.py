import unittest
from bs4 import BeautifulSoup
from scraper.analyzer import StructureAnalyzer

class TestStructureDetection(unittest.TestCase):
    def test_find_repeating_elements_with_class(self):
        html = """
        <html>
            <body>
                <div class="person-profile">
                    <h3>John Doe</h3>
                    <p>Email: john@example.com</p>
                </div>
                <div class="person-profile">
                    <h3>Jane Smith</h3>
                    <p>Email: jane@example.com</p>
                </div>
                <div class="person-profile">
                    <h3>Bob Jones</h3>
                    <p>Email: bob@example.com</p>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        elements = StructureAnalyzer.find_repeating_elements(soup)
        self.assertEqual(len(elements), 3)
        self.assertEqual(elements[0].name, 'div')
        self.assertIn('person-profile', elements[0]['class'])

    def test_find_repeating_elements_fallback(self):
        # No specific classes, but structurally similar
        html = """
        <html>
            <body>
                <div class="random-123">
                    <h3>John Doe</h3>
                    <p>Email: john@example.com</p>
                </div>
                <div class="random-456">
                    <h3>Jane Smith</h3>
                    <p>Email: jane@example.com</p>
                </div>
                <div class="random-789">
                    <h3>Bob Jones</h3>
                    <p>Email: bob@example.com</p>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        elements = StructureAnalyzer.find_repeating_elements(soup)
        
        # Should find them via structural similarity fallback
        self.assertEqual(len(elements), 3)
        
    def test_filter_table_headers(self):
        html = """
        <table>
            <tr>
                <th>Name</th>
                <th>Email</th>
            </tr>
            <tr>
                <td>John Doe</td>
                <td>john@example.com</td>
            </tr>
            <tr>
                <td>Jane Smith</td>
                <td>jane@example.com</td>
            </tr>
            <tr>
                <td>Bob Jones</td>
                <td>bob@example.com</td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, 'lxml')
        rows = soup.find_all('tr')
        filtered = StructureAnalyzer._filter_table_headers(rows)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0].find('td').text, 'John Doe')

if __name__ == '__main__':
    unittest.main()

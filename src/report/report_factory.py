import json
from pathlib import Path
from shutil import rmtree

from playwright.sync_api import sync_playwright
from seedir import seedir

from models.benchmark import Benchmark
from plotters.benchmark_plotter import BenchmarkPlotter
from statistics.benchmark_statistics import BenchmarkStatistics
from utils.benchmark_filter import filter_grouped_generators


class ReportFactory:
    def __init__(self, report_type: str = 'html'):
        self.report_type = report_type
        self.report = None

    def create_report(self, benchmark: Benchmark, output: Path, whitelist: list[str] = None,
                      blacklist: list[str] = None):
        """
        Create the report

        :param benchmark: The benchmark to create the report for
        :param output: The output path
        :param whitelist: The whitelist of generators to include in the report
        :param blacklist: The blacklist of generators to exclude from the report
        """
        if self.report_type.lower() == 'html':
            return self.create_html_report(benchmark, output, whitelist, blacklist)
        elif self.report_type.lower() == 'pdf':
            return self.create_pdf_report(benchmark, output, whitelist, blacklist)
        elif self.report_type.lower() == 'raw_data':
            return self.create_raw_report(benchmark, output, whitelist, blacklist)
        else:
            raise ValueError(f'Unknown report type \"{self.report_type}\"')

    @staticmethod
    def create_raw_report(benchmark: Benchmark, output: Path, whitelist: list[str] = None, blacklist: list[str] = None):
        """
        Create a raw report
        """
        grouped_generators = filter_grouped_generators(benchmark.report.generators_grouped, whitelist, blacklist)
        statistics = BenchmarkStatistics.create_statistics(grouped_generators)
        plots = BenchmarkPlotter.create_plots(grouped_generators)

        with open(output / 'benchmarks.json', 'w') as f:
            f.write(json.dumps(benchmark.report, indent=4))

        with open(output / 'statistics.json', 'w') as f:
            f.write(json.dumps(statistics, indent=4))

        images_dir = output / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        for name, bytesIO in plots.items():
            with open(images_dir / f'{name}.png', 'wb') as f:
                f.write(bytesIO.getvalue())

    def create_html_report(self, benchmark: Benchmark, output: Path, whitelist: list[str] = None,
                           blacklist: list[str] = None):
        """"
        Create an HTML report
        """
        grouped_generators = filter_grouped_generators(benchmark.report.generators_grouped, whitelist, blacklist)
        plots = BenchmarkPlotter.create_plots(grouped_generators)
        statistics = BenchmarkStatistics.create_statistics(grouped_generators)

        html_file = output / 'index.html'
        images_dir = output / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        for name, bytesIO in plots.items():
            with open(images_dir / f'{name}.png', 'wb') as f:
                f.write(bytesIO.getvalue())

        with open(html_file, 'w') as f:
            f.write('<html>\n')
            f.write('<head>\n')
            f.write(f"<title>GraphWalker Benchmark Report</title>\n")
            f.write('</head>\n')
            f.write('<body>\n')

            f.write(f"<h1>GraphWalker Benchmark Report: {benchmark.name}</h1>\n")

            f.write('<h2>Statistics</h2>\n')
            f.write('<table>\n')
            f.write('<tr><th>Statistic</th><th>Value</th></tr>\n')
            # TODO
            f.write('</table>\n')

            f.write('<h2>Plots</h2>\n')
            for name in plots.keys():
                f.write(f'<img src="images/{name}.png" alt="{name}">\n')

            f.write('</body>\n')
            f.write('</html>\n')

    def create_pdf_report(self, benchmark: Benchmark, output: Path, whitelist: list[str] = None,
                          blacklist: list[str] = None):
        """
        Create a PDF report
        """
        temp_dir = output / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=False)

        self.create_html_report(benchmark, temp_dir, whitelist, blacklist)

        playwright_instance = sync_playwright().start()
        chromium = playwright_instance.chromium
        browser = chromium.launch()
        page = browser.new_page()
        page.goto(f'file://{temp_dir.absolute()}/index.html')
        page.pdf(path=output / 'report.pdf')
        browser.close()
        playwright_instance.stop()

        # List files in temp directory, and give prompt to delete
        print(f'PDF report created at \"{output / "report.pdf"}\"')
        print(f'Temporary files are located at \"{temp_dir}\":')
        seedir(temp_dir)

        print('Delete temporary files? (y/n)')
        delete_temp = input()
        if delete_temp.lower() == 'y':
            rmtree(temp_dir)
        else:
            print(f'Files not deleted. Temporary files are located at \"{temp_dir}\"')
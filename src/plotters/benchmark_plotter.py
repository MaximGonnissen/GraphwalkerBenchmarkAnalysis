from io import BytesIO
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np

from models.benchmark import Benchmark
from models.benchmark_generator import BenchmarkGenerator


class BenchmarkPlotter:
    """
    A class used to plot the benchmark results
    """
    benchmark: Benchmark

    @staticmethod
    def get_plot_functions() -> dict[str, Callable[[dict[str, list[BenchmarkGenerator]]], None]]:
        """
        Get the available plot functions

        :return: a dictionary with the available plot functions
        """
        return {'Total Time': BenchmarkPlotter.plot_total_time, 'Total Size': BenchmarkPlotter.plot_total_size,
                'Average Time': BenchmarkPlotter.plot_average_time, 'Average Size': BenchmarkPlotter.plot_average_size,
                'Minimum Time': BenchmarkPlotter.plot_minimum_time, 'Maximum Time': BenchmarkPlotter.plot_maximum_time,
                'Minimum Size': BenchmarkPlotter.plot_minimum_size, 'Maximum Size': BenchmarkPlotter.plot_maximum_size,
                'Max-Min Size': BenchmarkPlotter.plot_max_minus_min_size,
                'Max-Min Time': BenchmarkPlotter.plot_max_minus_min_time,
                'Coverage vs Time': BenchmarkPlotter.plot_coverage_vs_time,
                'Size over Time': BenchmarkPlotter.plot_average_size_divided_by_average_time,
                'Average Vertex Visits %': BenchmarkPlotter.plot_average_vertex_percentage_total_visits,
                'Average Edge Visits %': BenchmarkPlotter.plot_average_edge_percentage_total_visits,
                'Average vs Minimum Time': BenchmarkPlotter.plot_average_vs_minimum_time,
                'Average vs Minimum Size': BenchmarkPlotter.plot_average_vs_minimum_size}

    @staticmethod
    def get_per_coverage_plot_functions() -> dict[str, Callable[[dict[str, list[BenchmarkGenerator]], int], None]]:
        """
        Get the available plot functions that are run per coverage value

        :return: a dictionary with the available plot functions
        """
        return {'Histogram Total Visited Vertices': BenchmarkPlotter.plot_histogram_total_visited_vertices,
                'Histogram Total Visited Edges': BenchmarkPlotter.plot_histogram_total_visited_edges,
                'Histogram Average Visited Vertices': BenchmarkPlotter.plot_histogram_average_visited_vertices,
                'Histogram Average Visited Edges': BenchmarkPlotter.plot_histogram_average_visited_edges}

    @staticmethod
    def get_test_execution_plot_functions() -> dict[
        str, Callable[[Benchmark, dict[str, list[BenchmarkGenerator]]], None]]:
        """
        Get the available plot functions that are run per coverage value

        :return: a dictionary with the available plot functions
        """
        return {'Average Test Execution Time': BenchmarkPlotter.plot_average_test_execution_time,
                'Minimum Test Execution Time': BenchmarkPlotter.plot_minimum_test_execution_time,
                'Maximum Test Execution Time': BenchmarkPlotter.plot_maximum_test_execution_time}

    @staticmethod
    def create_plots(benchmark: Benchmark, grouped_generators: dict[str, list[BenchmarkGenerator]],
                     show: bool = False) -> dict[str, BytesIO]:
        """
        Plot the benchmark results

        :param benchmark: The benchmark to plot
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param show: bool: Whether to show the plots
        """
        BenchmarkPlotter.benchmark = benchmark
        plt.close()
        plots: dict[str, BytesIO] = {}

        # General bar plots
        for plot_function_name, plot_function in BenchmarkPlotter.get_plot_functions().items():
            plt.close()
            plot_function(grouped_generators)
            if show:
                plt.show()
            plots[plot_function_name] = BenchmarkPlotter.save_plot_bytesio()

        # Test execution bar plots
        if all([run_group.successful_runs for run_group in benchmark.run_groups]):
            for plot_function_name, plot_function in BenchmarkPlotter.get_test_execution_plot_functions().items():
                plt.close()
                plot_function(benchmark, grouped_generators)
                if show:
                    plt.show()
                plots[plot_function_name] = BenchmarkPlotter.save_plot_bytesio()

        # Prepare coverage values
        coverage_values = []
        for generator_group in grouped_generators:
            for generator in grouped_generators[generator_group]:
                if generator.stop_coverage not in coverage_values:
                    coverage_values.append(generator.stop_coverage)

        coverage_values.sort()

        # Per coverage plots
        for plot_function_name, plot_function in BenchmarkPlotter.get_per_coverage_plot_functions().items():
            for coverage_value in coverage_values:
                plt.close()
                plot_function(grouped_generators, coverage_value)
                if show:
                    plt.show()
                plots[f'{plot_function_name} - {coverage_value}%'] = BenchmarkPlotter.save_plot_bytesio()

        return plots

    @staticmethod
    def _post_process_plot(fig, ax):
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()

    @staticmethod
    def _plot_bars(fig, ax, grouped_generators: dict[str, list[BenchmarkGenerator]],
                   value_lambda: Callable[[BenchmarkGenerator], int | float], add_trend_line: bool = True):
        """
        Plot results for a list of benchmark generators
        :param fig: The figure to plot on
        :param ax: The axis to plot on
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param value_lambda: The lambda function to get the value to plot
        :param add_trend_line: Whether to add a trend line to the plot
        :return:
        """
        group_count = len(grouped_generators)
        bar_width = 6 / group_count

        for i, generator_group in enumerate(grouped_generators):
            coverage_values = [generator.stop_coverage + i * bar_width for generator in
                               grouped_generators[generator_group]]
            property_values = [value_lambda(generator) for generator in grouped_generators[generator_group]]

            ax.bar(coverage_values, property_values, label=generator_group, width=bar_width, align='center')

            if add_trend_line:
                coefficients = np.polyfit(coverage_values, property_values, 3)
                trend_line_function = np.poly1d(coefficients)
                ax.plot(coverage_values, trend_line_function(coverage_values), linestyle='--', linewidth=1, alpha=0.7)

        ax.set_xticks([generator.stop_coverage for generator in grouped_generators[next(iter(grouped_generators))]])
        ax.yaxis.grid(True)

        BenchmarkPlotter._post_process_plot(fig, ax)

    @staticmethod
    def _plot_bars_tests(fig, ax, benchmark: Benchmark, grouped_generators: dict[str, list[BenchmarkGenerator]],
                         value_lambda: Callable[[BenchmarkGenerator], int | float], add_trend_line: bool = True):
        """
        Plot results for test runs, given a list of benchmark generators to use as filters
        """
        group_count = len(grouped_generators)
        bar_width = 6 / group_count

        grouped_run_groups = {}
        for run_group in benchmark.run_groups_sorted:
            if run_group.algorithm not in grouped_generators.keys():
                continue    # Skip algorithms that are not in the grouped_generators
            if run_group.algorithm not in grouped_run_groups:
                grouped_run_groups[run_group.algorithm] = []
            grouped_run_groups[run_group.algorithm].append(run_group)

        for i, algorithm in enumerate(grouped_run_groups):
            coverage_values = [run_group.stop_coverage + i * bar_width for run_group in
                               grouped_run_groups[algorithm]]
            property_values = [value_lambda(run_group) for run_group in grouped_run_groups[algorithm]]

            ax.bar(coverage_values, property_values, label=algorithm, width=bar_width, align='center')

            if add_trend_line:
                coefficients = np.polyfit(coverage_values, property_values, 3)
                trend_line_function = np.poly1d(coefficients)
                ax.plot(coverage_values, trend_line_function(coverage_values), linestyle='--', linewidth=1, alpha=0.7)

        ax.set_xticks([run_group.stop_coverage for run_group in grouped_run_groups[next(iter(grouped_run_groups))]])
        ax.yaxis.grid(True)

        BenchmarkPlotter._post_process_plot(fig, ax)

    @staticmethod
    def _plot_lines(fig, ax, grouped_generators: dict[str, list[BenchmarkGenerator]],
                    value_lambda: Callable[[BenchmarkGenerator], int]):
        """
        Plot results for a list of benchmark generators
        :param fig: The figure to plot on
        :param ax: The axis to plot on
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param value_lambda: The lambda function to get the value to plot
        :return:
        """
        for generator_group in grouped_generators:
            coverage_values = [generator.stop_coverage for generator in grouped_generators[generator_group]]
            property_values = [value_lambda(generator) for generator in grouped_generators[generator_group]]

            ax.plot(coverage_values, property_values, label=generator_group)

        ax.set_xticks([generator.stop_coverage for generator in grouped_generators[next(iter(grouped_generators))]])
        ax.yaxis.grid(True)

        BenchmarkPlotter._post_process_plot(fig, ax)

    @staticmethod
    def plot_total_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the total time taken for each generator in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Total generation time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Total Time (μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.total_generation_time)

    @staticmethod
    def plot_total_size(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the total size of each generator's path in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Total test suite size per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Total Size (element count)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.total_test_suite_size)

    @staticmethod
    def plot_average_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the average time taken for each generator in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Average generation time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Average Time (μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.average_generation_time)

    @staticmethod
    def plot_average_size(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the average size of each generator's path in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Average test suite size per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Average Size (element count)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.average_test_suite_size)

    @staticmethod
    def plot_minimum_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the minimum time taken for each generator in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Minimum generation time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Minimum Time (μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.min_generation_time)

    @staticmethod
    def plot_maximum_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the maximum time taken for each generator in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Maximum generation time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Maximum Time (μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.max_generation_time)

    @staticmethod
    def plot_minimum_size(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the minimum size of each generator's path in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Minimum test suite size per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Minimum Size (element count)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.min_test_suite_size)

    @staticmethod
    def plot_maximum_size(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the maximum size of each generator's path in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Maximum test suite size per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Maximum Size (element count)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: generator.max_test_suite_size)

    @staticmethod
    def plot_max_minus_min_size(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the difference between the maximum and minimum size of each generator's path in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Difference between maximum and minimum test suite size\nper generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Difference (element count)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators,
                                    lambda generator: generator.max_test_suite_size - generator.min_test_suite_size)

    @staticmethod
    def plot_max_minus_min_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the difference between the maximum and minimum time of each generator's path in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Difference between maximum and minimum generation time\nper generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Difference (μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators,
                                    lambda generator: generator.max_generation_time - generator.min_generation_time)

    @staticmethod
    def plot_coverage_vs_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the coverage vs time for each generator in the benchmark

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Coverage vs Generation time per generator')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Time (μs)')

        BenchmarkPlotter._plot_lines(fig, ax, grouped_generators, lambda generator: generator.total_generation_time)

    @staticmethod
    def plot_average_size_divided_by_average_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the average size of each generator's path divided by the average time taken for each generator in the benchmark

        --> Higher values indicate a more efficient generator because it generates more elements in less time?

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Average test suite size divided by\naverage generation time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Size/Time (element count/μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda
            generator: generator.average_test_suite_size / generator.average_generation_time)

    @staticmethod
    def _plot_histogram(fig, ax, grouped_generators: dict[str, list[BenchmarkGenerator]],
                        property_lambda: Callable[[BenchmarkGenerator], dict], coverage_value):
        """
        Plot the histogram of a property for each generator in the benchmark, for a specific coverage value

        :param fig: The figure to plot on
        :param ax: The axis to plot on
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param property_lambda: The lambda function to get the property to use
        :param coverage_value: The coverage value to plot the histogram for
        """
        for generator_group in grouped_generators:
            for i, generator in enumerate(grouped_generators[generator_group]):
                if generator.stop_coverage != coverage_value:
                    continue

                items = [item[0] for item in
                         sorted(property_lambda(generator).items(), key=lambda x: x[1], reverse=True)]
                item_visits = [int(item[1]) for item in
                               sorted(property_lambda(generator).items(), key=lambda x: x[1], reverse=True)]
                ax.hist(items, weights=item_visits, bins=len(items), label=generator_group, alpha=0.5)

        ax.set_xticks([])
        BenchmarkPlotter._post_process_plot(fig, ax)

    @staticmethod
    def plot_histogram_total_visited_vertices(grouped_generators: dict[str, list[BenchmarkGenerator]], coverage_value):
        """
        Plot the histogram of visited vertices for each generator in the benchmark, for a specific coverage value (since this would otherwise be hard to read)

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param coverage_value: The coverage value to plot the histogram for
        """
        fig, ax = plt.subplots()

        ax.set_title(f'Vertex total visit count histogram for\ncoverage value {coverage_value}%')
        ax.set_xlabel(f"Vertex")
        ax.set_ylabel('Visit Count')

        BenchmarkPlotter._plot_histogram(fig, ax, grouped_generators,
                                         lambda generator: generator.total_vertex_visits_individual, coverage_value)

    @staticmethod
    def plot_histogram_total_visited_edges(grouped_generators: dict[str, list[BenchmarkGenerator]], coverage_value):
        """
        Plot the histogram of visited edges for each generator in the benchmark, for a specific coverage value (since this would otherwise be hard to read)

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param coverage_value: The coverage value to plot the histogram for
        """
        fig, ax = plt.subplots()

        ax.set_title(f'Edge total visit count histogram for\ncoverage value {coverage_value}%')
        ax.set_xlabel(f"Edge")
        ax.set_ylabel('Visit Count')

        BenchmarkPlotter._plot_histogram(fig, ax, grouped_generators,
                                         lambda generator: generator.total_edge_visits_individual, coverage_value)

    @staticmethod
    def plot_histogram_average_visited_vertices(grouped_generators: dict[str, list[BenchmarkGenerator]],
                                                coverage_value):
        """
        Plot the histogram of visited vertices for each generator in the benchmark, for a specific coverage value (since this would otherwise be hard to read)

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param coverage_value: The coverage value to plot the histogram for
        """
        fig, ax = plt.subplots()

        ax.set_title(f'Vertex average visit count histogram for\ncoverage value {coverage_value}%')
        ax.set_xlabel(f"Vertex")
        ax.set_ylabel('Visit Count')

        BenchmarkPlotter._plot_histogram(fig, ax, grouped_generators,
                                         lambda generator: generator.average_vertex_visits_individual, coverage_value)

    @staticmethod
    def plot_histogram_average_visited_edges(grouped_generators: dict[str, list[BenchmarkGenerator]], coverage_value):
        """
        Plot the histogram of visited edges for each generator in the benchmark, for a specific coverage value (since this would otherwise be hard to read)

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        :param coverage_value: The coverage value to plot the histogram for
        """
        fig, ax = plt.subplots()

        ax.set_title(f'Edge average visit count histogram for\ncoverage value {coverage_value}%')
        ax.set_xlabel(f"Edge")
        ax.set_ylabel('Visit Count')

        BenchmarkPlotter._plot_histogram(fig, ax, grouped_generators,
                                         lambda generator: generator.average_edge_visits_individual, coverage_value)

    @staticmethod
    def plot_average_vertex_percentage_total_visits(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the percentage of unique vertex visits in an average traversal (e.g. 78% of vertices visited)

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Percentage of unique vertices visited\nin an average traversal')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Average Percentage (%)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: [1 for vertex_visits in
                                                                                    generator.average_vertex_visits_individual.values()
                                                                                    if vertex_visits != 0].count(
            1) / BenchmarkPlotter.benchmark.report.model.vertices * 100)

    @staticmethod
    def plot_average_edge_percentage_total_visits(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the percentage of unique edge visits in an average traversal (e.g. 78% of edges visited)

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name

        :remark: This will not reach the proper coverage percentage, as some edges' average visit count is < 0.5, and rounded to a long by the generator
        """
        fig, ax = plt.subplots()

        ax.set_title('Percentage of unique edges visited\nin an average traversal')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Average Percentage (%)')
        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators, lambda generator: [1 for edge_visits in
                                                                                    generator.average_edge_visits_individual.values()
                                                                                    if edge_visits != 0].count(
            1) / BenchmarkPlotter.benchmark.report.model.edges * 100)

    @staticmethod
    def plot_average_vs_minimum_time(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the difference between the average and minimum time of each generator's path in the benchmark,
        to give an indication of how optimistic a minimum time is

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Average generation time compared to minimum generation time\nper generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Time (μs)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators,
                                    lambda generator: generator.average_generation_time - generator.min_generation_time)

    @staticmethod
    def plot_average_vs_minimum_size(grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the difference between the average and minimum size of each generator's path in the benchmark,
        to give an indication of how optimistic a minimum size is

        :param grouped_generators: The generator benchmarks to plot, grouped by generator name
        """
        fig, ax = plt.subplots()

        ax.set_title('Average test suite size compared to minimum test suite size\nper generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Size (element count)')

        BenchmarkPlotter._plot_bars(fig, ax, grouped_generators,
                                    lambda generator: generator.average_test_suite_size - generator.min_test_suite_size)

    @staticmethod
    def plot_average_test_execution_time(benchmark: Benchmark, grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the average time taken to execute a test suite

        :param benchmark: The benchmark object to get run information from
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name, to use for filtering
        """
        fig, ax = plt.subplots()

        ax.set_title('Average test execution time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Average Time (μs)')

        BenchmarkPlotter._plot_bars_tests(fig, ax, benchmark, grouped_generators,
                                          lambda run_group: run_group.average_test_duration)

    @staticmethod
    def plot_minimum_test_execution_time(benchmark: Benchmark, grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the minimum time taken to execute a test suite

        :param benchmark: The benchmark object to get run information from
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name, to use for filtering
        """
        fig, ax = plt.subplots()

        ax.set_title('Minimum test execution time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Minimum Time (μs)')

        BenchmarkPlotter._plot_bars_tests(fig, ax, benchmark, grouped_generators,
                                          lambda run_group: run_group.minimum_test_duration)

    @staticmethod
    def plot_maximum_test_execution_time(benchmark: Benchmark, grouped_generators: dict[str, list[BenchmarkGenerator]]):
        """
        Plot the maximum time taken to execute a test suite

        :param benchmark: The benchmark object to get run information from
        :param grouped_generators: The generator benchmarks to plot, grouped by generator name, to use for filtering
        """
        fig, ax = plt.subplots()

        ax.set_title('Maximum test execution time per generator by coverage value')
        ax.set_xlabel('Coverage (%)')
        ax.set_ylabel('Maximum Time (μs)')

        BenchmarkPlotter._plot_bars_tests(fig, ax, benchmark, grouped_generators,
                                          lambda run_group: run_group.maximum_test_duration)

    @staticmethod
    def save_plot(output: str):
        """
        Save the plot to a file

        :param output: str: The path to save the plot
        """
        plt.savefig(output)

    @staticmethod
    def save_plot_bytesio() -> BytesIO:
        """
        Save the plot to a BytesIO object
        """
        bytesio = BytesIO()
        plt.savefig(bytesio, format='png', dpi=300)
        return bytesio

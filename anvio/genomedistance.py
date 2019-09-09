#!/usr/bin/env python
# -*- coding: utf-8
"""Code for genome distance calculation"""

import os
import shutil
import pandas as pd

import anvio
import anvio.utils as utils
import anvio.terminal as terminal
import anvio.filesnpaths as filesnpaths
import anvio.genomedescriptions as genomedescriptions

from itertools import combinations

from anvio.errors import ConfigError
from anvio.drivers import pyani, sourmash
from anvio.tables.miscdata import TableForLayerAdditionalData
from anvio.tables.miscdata import TableForLayerOrders

__author__ = "Developers of anvi'o (see AUTHORS.txt)"
__copyright__ = "Copyleft 2015-2019, the Meren Lab (http://merenlab.org/)"
__credits__ = []
__license__ = "GPL 3.0"
__version__ = anvio.__version__
__maintainer__ = "Mahmoud Yousef"
__email__ = "mahmoudyousef@uchicago.edu"

run = terminal.Run()
progress = terminal.Progress()

J = lambda *args: os.path.join(*args)


class Dereplicate:
    def __init__(self, args):
        self.args = args

        A = lambda x, t: t(args.__dict__[x]) if x in args.__dict__ else None
        null = lambda x: x

        # input
        self.internal_genomes = A('internal_genomes', null)
        self.external_genomes = A('external_genomes', null)
        self.fasta_text_file = A('fasta_text_file', null)
        self.ani_dir = A('ani_dir', null)
        self.mash_dir = A('mash_dir', null)
        # mode
        self.program_name = A('program', null) or 'pyANI'
        self.representative_method = A('representative_method', null)
        self.distance_threshold = A('distance_threshold', null)
        # pyANI specific
        self.min_alignment_fraction = A('min_alignment_fraction', null)
        self.significant_alignment_length = A('significant_alignment_length', null)
        self.min_percent_identity = A('min_percent_identity', null)
        self.use_full_percent_identity = A('use_full_percent_identity', null)
        # sourmash specific
        self.distance_threshold = A('distance_threshold', null)
        # output
        self.output_dir = A('output_dir', null)
        self.report_all = A('report_all', null)
        self.just_do_it = A('just_do_it', null)

        self.import_previous_results = False
        self.sequence_source_provided = False

        self.sanity_check()
        self.distance_metric_name = self.get_distance_metric_name()

        self.clusters = {}
        self.cluster_report = {}
        self.genomes_info_dict = {}
        self.cluster_to_representative = {}
        self.genome_name_to_cluster_name = {}


    def get_distance_metric_name(self):
        if self.program_name in ['pyANI']:
            return 'percentage_identity' if not self.use_full_percent_identity else 'full_percentage_identity'
        elif self.program_name in ['sourmash']:
            return 'mash_distance'


    def is_genome_names_compatible_with_distance_matrix(self, distance_matrix, genome_names):
        matrix_names = distance_matrix.keys()

        missing_in_matrix = [n for n in genome_names if n not in distance_matrix]
        missing_in_names = [n for n in distance_matrix if n not in genome_names]

        should_raise = False
        if len(missing_in_matrix):
            should_raise = True
            raise_info = ('sequence source names', 'distance matrix',
                          missing_in_matrix[:5] if len(missing_in_matrix) < 6 else missing_in_matrix)
        elif len(missing_in_names):
            should_raise = True
            raise_info = ('distance matrix names', 'sequence sources',
                          missing_in_names[:5] if len(missing_in_names) < 6 else missing_in_names)

        if should_raise:
            raise ConfigError("At least one of your %s does not appear in the %s. This could be due\
                               to many different reasons. Probably, the imported distance results were generated from sequence sources\
                               that are somehow different from the ones you provided here. If you imported your results (e.g\
                               with --ani-dir, --mash-dir, etc), we recommend re-running with standard inputs.\
                               See `INPUT OPTIONS` within the help menu. Here are some that are missing: %s." % (*raise_info, ))


    def sanity_check(self):
        if any([self.fasta_text_file, self.external_genomes, self.internal_genomes]):
            self.sequence_source_provided = True

        if not any([self.program_name, self.ani_dir, self.mash_dir]):
            raise ConfigError("Anvi'o could not determine how you want to dereplicate\
                              your genomes. Please take a close look at your parameters: either --program needs to be\
                              set, or an importable directory (e.g. --ani-dir, --mash-dir, etc) needs to be provided.")

        if self.program_name not in ['pyANI', 'sourmash']:
            raise ConfigError("Anvi'o is impressed by your dedication to dereplicate your genomes through %s, but\
                              %s is not compatible with `anvi-dereplicate-genomes`. Anvi'o can only work with pyANI\
                              and sourmash separately." % (self.program_name, self.program_name))

        if self.ani_dir and self.mash_dir:
            raise ConfigError("Anvi'o cannot currently dereplicate using both ANI and mash distance results at\
                              the same time. Please pick one to use for dereplication")

        if self.ani_dir or self.mash_dir:
            self.import_previous_results = True

            if self.sequence_source_provided:
                additional_msg = ''

                if not self.just_do_it:
                    raise ConfigError("You provided any of {--external-genomes, --internal-genomes, --fasta-text-file}\
                                       *alongside* a results directory. This requires that the external, internal,\
                                       and fasta inputs are exactly those used to generate the results directory.\
                                       This is sketchy and anvi'o doesn't recommend it. If you insist, re-run with\
                                       --just-do-it. Otherwise, have the results regenerated here by removing '%s'\
                                       as an input." % (self.ani_dir or self.mash_dir))
            else:
                additional_msg = (' In addition, no FASTAs will be generated since you did not provide any sequence '
                                  'sources for anvi\'o.')

            run.warning("You chose to work with an already existing results folder. Please keep in mind that you\
                         are now burdened with the responsibility of knowing what parameters you used to generate\
                         these results.%s" % additional_msg)

        if self.ani_dir and not self.program_name in ['pyANI']:
            run.warning("You provided a pre-existing directory of ANI results (--ani-dir), but also provided a program\
                        name ('%s') that was not compatible with ANI. Anvi'o knows that you want to use the pre-existing\
                        results, so she cunningly ignores this slip-up." % self.program_name)
            self.program_name = 'pyANI'

        if self.mash_dir and not self.program_name in ['sourmash']:
            run.warning("You provided a pre-existing directory of mash results (--mash-dir), but also provided a program\
                        name ('%s') that was not compatible with mash. Anvi'o knows that you want to use the pre-existing\
                        results, so she cunningly ignores this slip-up." % self.program_name)
            self.program_name = 'sourmash'

        if self.min_alignment_fraction < 0 or self.min_alignment_fraction > 1:
            if self.program_name == "pyANI":
                raise ConfigError("Alignment coverage is a value between 0 and 1. Your cutoff alignment coverage\
                                  value of %.2f doesn't fit in these boundaries" % self.min_alignment_fraction)

        if self.distance_threshold < 0 or self.distance_threshold > 1:
            raise ConfigError("When anvi'o collapses %s's output into a distance matrix, all values are reported as\
                              distances between 0 and 1. %.2f can't be used to determine redundant genomes"\
                              % (self.program_name, self.distance_threshold))

        if self.representative_method == "Qscore" and not (self.external_genomes or self.internal_genomes):
                self.representative_method = "distance"
                run.warning("Anvi'o must be provided either an external or internal genome collection (or both) to be\
                             used with Qscore, since this is the only way for anvi'o to learn about completion and\
                             redundancy scores. Anvi'o will switch to 'distance'")


    def init_genome_distance(self):
        if self.program_name == "pyANI":
            self.distance = ANI(self.args)
        else:
            assert self.program_name == "sourmash", "Fatal error in self.program_name assertion in initialization. Please inform the developers."
            self.distance = SourMash(self.args)


    def get_genome_names(self):
        """
        genome_names are learned from the GenomeDistance class in self.distance.__init__. But if distance scores are
        imported and sequence sources were not provided, GenomeDistance obviously knows nothing of the genome_names. So
        in this fringe case we grab genome names from the results matrix
        """
        return self.distance.genome_names if self.distance.genome_names \
                                          else set(self.distance_matrix.keys())


    def get_distance_matrix(self):
        return self.import_distance_matrix() if self.import_previous_results else self.gen_distance_matrix()


    def gen_distance_matrix(self):
        self.distance.process(self.temp_dir)

        distance_matrix = self.distance.results[self.distance_metric_name]

        run.info('%s distance metric' % self.program_name, 'calculated')

        if anvio.DEBUG:
            import json
            for report in self.distance.results:
                run.warning(None, header=report)
                print(json.dumps(self.distance.results[report], indent=2))

        return distance_matrix


    def import_distance_matrix(self):
        dir_name, dir_path = ('--ani-dir', self.ani_dir) if self.program_name in ['pyANI'] else ('--mash-dir', self.mash_dir)

        necessary_reports = [self.distance_metric_name] + (['alignment_coverage'] if self.program_name in ['pyANI'] else [])

        if filesnpaths.is_dir_empty(dir_path):
            raise ConfigError("The %s you provided is empty. What kind of game are you playing?" % dir_name)
        files_in_dir = os.listdir(self.ani_dir)

        for report in necessary_reports:
            report_name = report + ".txt"
            matching_filepaths = [f for f in files_in_dir if report_name in f]

            if self.distance_metric_name == 'percentage_identity':
                # FIXME very very bad block of code here. Why should this method know about
                # percentage_identity or full_percentage_identity?
                matching_filepaths = [f for f in matching_filepaths if 'full_percentage_identity' not in f]

            if len(matching_filepaths) > 1:
                raise ConfigError("Your results directory contains multiple text files for the matrix %s.\
                                  Please clean up your directory and make sure that only one text file of this\
                                  report exists" % report)
            elif not len(matching_filepaths):
                raise ConfigError("Your results directory does not have a text file for the report %s.\
                                  Anvi'o cannot dereplicate genomes from prevous results without this report" % report)

            self.distance.results[report] = utils.get_TAB_delimited_file_as_dictionary(J(dir_path, matching_filepaths[0]))

        run.info('%s results directory imported from' % self.program_name, dir_path)

        return self.distance.results[self.distance_metric_name]


    def clean(self):
        if self.temp_dir:
            if anvio.DEBUG:
                run.warning("The temp directory, %s, is kept. Please don't forget to clean it up\
                             later" % self.temp_dir, header="Debug")
            else:
                run.info_single('Cleaning up the temp directory (you can use `--debug` if you would\
                                 like to keep it for testing purposes)', nl_before=1, nl_after=1)

                shutil.rmtree(self.temp_dir)
                self.temp_dir = None


    def report(self):
        if self.sequence_source_provided:
            self.populate_genomes_dir()
        if not self.import_previous_results:
            self.populate_distance_scores_dir()

        # FIXME df.to_csv(self.GENOME_GROUPS_path, sep='\t', index=False)


    def populate_genomes_dir(self):
        if self.report_all:
            paths = {name: path for name, path in self.distance.name_to_temp_path.items()}
        else:
            paths = {name: path for name, path in self.distance.name_to_temp_path.items() if name in self.cluster_to_representative.values()}

        for name, path in paths.items():
            shutil.copy(src = path, dst = J(self.GENOMES_dir, name + '.fa'))


    def populate_distance_scores_dir(self):
        for f in os.listdir(J(self.temp_dir, 'output')):
            shutil.copy(src = J(self.temp_dir, 'output', f),
                        dst = J(self.DISTANCE_SCORES_dir, f))


    def init_output_dir(self):
        """
        DIRECTORY STRUCTURE:
        ===================
            output_dir/
            ├── GENOMES/
            ├── DISTANCE_SCORES/
            └── GENOME_GROUPS.txt

        GENOMES/
            A folder with genomes. Each genome is a fasta file. Not provided if no sequence sources
            are provided.
        DISTANCE_SCORES/
            A folder containing the output of distance scores. Not provided if previous distance
            scores are imported.
        GENOME_GROUPS.txt
            A text file detailing which genomes were determined to be redundant with one another.
            Headers: `genome_name`, `group`, `path`. If previous distance scores are imported, `path` is
            not included.
        """
        filesnpaths.check_output_directory(self.output_dir, ok_if_exists=False)
        os.mkdir(self.output_dir)

        self.GENOME_GROUPS_path = J(self.output_dir, 'GENOME_GROUPS.txt')

        if self.sequence_source_provided:
            self.GENOMES_dir = J(self.output_dir, 'GENOMES')
            os.mkdir(self.GENOMES_dir)
        else:
            self.GENOMES_dir = None

        if not self.import_previous_results:
            self.DISTANCE_SCORES_dir = J(self.output_dir, 'DISTANCE_SCORES')
            os.mkdir(self.DISTANCE_SCORES_dir)
        else:
            self.DISTANCE_SCORES_dir = None


    def process(self):
        run.info('Run mode', self.program_name)

        self.init_output_dir()

        # inits self.distance
        self.init_genome_distance()

        # will hold a directory of fasta files to calculate distance matrix
        self.temp_dir = self.distance.get_fasta_sequences_dir() if self.sequence_source_provided else None

        self.distance_matrix = self.get_distance_matrix()
        self.genome_names = self.get_genome_names()

        self.is_genome_names_compatible_with_distance_matrix(self.distance_matrix, self.genome_names)

        run.info('Number of genomes considered', len(self.genome_names))


        self.init_clusters()
        self.populate_genomes_info_dict()
        self.dereplicate()


    def init_clusters(self):
        """Each genome starts in its own cluster, i.e. as many clusters as genomes"""
        for count, genome_name in enumerate(self.genome_names, start=1):
            cluster_name = 'cluster_%06d' % count
            self.genome_name_to_cluster_name[genome_name] = cluster_name
            self.clusters[cluster_name] = [genome_name]


    def populate_genomes_info_dict(self):
        full_dict = {}

        if self.distance.genome_desc:
            full_dict = self.distance.genome_desc.genomes

        if self.distance.fasta_txt:
            fastas = utils.get_TAB_delimited_file_as_dictionary(self.distance.fasta_txt, expected_fields=['name', 'path'], only_expected_fields=True)

            for name in fastas:
                full_dict[name] = {}
                full_dict[name]['percent_completion'] = 0
                full_dict[name]['percent_redundancy'] = 0
                full_dict[name]['total_length'] = sum(utils.get_read_lengths_from_fasta(fastas[name]['path']).values())

        self.genomes_info_dict = full_dict


    def update_clusters(self, genome1, genome2):
        from_cluster = self.genome_name_to_cluster_name[genome1]
        to_cluster = self.genome_name_to_cluster_name[genome2]

        if from_cluster == to_cluster:
            return

        for genome in self.clusters[from_cluster]:
            self.clusters[to_cluster].append(genome)
            self.genome_name_to_cluster_name[genome] = to_cluster
            self.clusters[from_cluster].remove(genome)


    def are_redundant(self, genome1, genome2):
        cluster1 = self.genome_name_to_cluster_name[genome1]
        cluster2 = self.genome_name_to_cluster_name[genome2]
        return True if cluster1 == cluster2 else False


    def gen_cluster_report(self):
        if not any([self.clusters, self.cluster_to_representative]):
            raise ConfigError("gen_cluster_report :: Run dereplicate() before trying to generate a cluster report")

        self.cluster_report = {
            cluster_name: {
                'representative': self.cluster_to_representative[cluster_name],
                'genomes': self.clusters[cluster_name]
            } for cluster_name in self.clusters
        }


    def rename_clusters(self):
        new_cluster_names = ['cluster_%06d' % count for count in range(1, len(self.clusters) + 1)]
        self.clusters = {new_cluster_name: genomes for new_cluster_name, genomes in zip(new_cluster_names, self.clusters.values())}


    def dereplicate(self):
        progress.new('Dereplication', progress_total_items = sum(1 for _ in combinations(self.genome_names, 2)))

        genome_pairs = combinations(self.genome_names, 2)
        for genome1, genome2 in genome_pairs:
            progress.increment()
            progress.update('Comparing %s with %s' % (genome1, genome2))

            if genome1 == genome2 or self.are_redundant(genome1, genome2):
                continue

            distance = float(self.distance_matrix[genome1][genome2])
            if distance > self.distance_threshold:
                self.update_clusters(genome1, genome2)

        # remove empty clusters and rename so that names are sequential
        self.clusters = {cluster: genomes for cluster, genomes in self.clusters.items() if genomes}
        self.rename_clusters()

        self.cluster_to_representative = self.get_representative_for_each_cluster()
        self.gen_cluster_report()

        progress.end()

        run.info('Number of redundant genomes', len(self.genome_names) - len(self.cluster_report))
        run.info('Final number of dereplicated genomes', len(self.cluster_report))

        if anvio.DEBUG:
            import json
            for name in self.cluster_report.keys():
                run.warning(None, header=name)
                print(json.dumps(self.cluster_report[name], indent=2))


    def pick_best_of_two(self, one, two):
        if not one and not two:
            return None
        elif not one and len(two) == 1:
            return two[0]
        elif not two and len(one) == 1:
            return one[0]

        best_one = self.pick_representative(one)
        best_two = self.pick_representative(two)

        if not best_one and best_two:
            return best_two
        elif not best_two and best_one:
            return best_one

        try:
            score1 = self.genomes_info_dict[best_one]['percent_completion'] - self.genomes_info_dict[best_one]['percent_redundancy']
        except:
            raise ConfigError("At least one of your genomes does not contain completion or redundancy estimates. Here is an example: %s." % best_one)
        try:
            score2 = self.genomes_info_dict[best_two]['percent_completion'] - self.genomes_info_dict[best_two]['percent_redundancy']
        except:
            raise ConfigError("At least one of your genomes does not contain completion or redundancy estimates. Here is an example: %s." % best_two)

        if score1 > score2:
            return best_one
        elif score2 > score1:
            return best_two
        else:
            len1 = self.genomes_info_dict[best_one]['total_length']
            len2 = self.genomes_info_dict[best_two]['total_length']

            if len2 > len1:
                return best_two
            else:
                return best_one


    def pick_representative(self, cluster):
        if not cluster:
            return None
        elif len(cluster) == 1:
            return cluster[0]

        medium = int(len(cluster) / 2)
        best = self.pick_best_of_two(cluster[:medium], cluster[medium:])

        return best


    def pick_longest_representative(self, cluster):
        max_name = cluster[0]
        max_val = self.genomes_info_dict[max_name]['total_length']

        for name in cluster[1:]:
            val = self.genomes_info_dict[name]['total_length']

            if val > max_val:
                max_name = name
                max_val = val

        return max_name


    def pick_closest_distance(self, cluster):
        d = {}
        for name in cluster:
            d[name] = 0

            for target in cluster:
                d[name] += float(self.distance_matrix[name][target])

        new_dict = {}
        for name, val in d.items():
            new_dict[val] = name

        max_val = max(new_dict.keys())

        return new_dict[max_val]


    def get_representative_for_each_cluster(self):
        cluster_to_representative = {}
        for cluster_name in self.clusters.keys():
            cluster = self.clusters[cluster_name]

            if cluster == []:
                continue

            if self.representative_method == "Qscore":
                representative_name = self.pick_representative(cluster)
            elif self.representative_method == "length":
                representative_name = self.pick_longest_representative(cluster)
            elif self.representative_method == "distance":
                representative_name = self.pick_closest_distance(cluster)

            cluster_to_representative[cluster_name] = representative_name

        return cluster_to_representative



class GenomeDistance:
    def __init__(self, args):
        self.args = args

        A = lambda x, t: t(args.__dict__[x]) if x in args.__dict__ else None
        null = lambda x: x
        self.fasta_txt = A('fasta_text_file', null)
        self.internal_genomes = A('internal_genomes', null)
        self.external_genomes = A('external_genomes', null)

        if (self.internal_genomes or self.external_genomes):
            self.genome_desc = genomedescriptions.GenomeDescriptions(args, run = terminal.Run(verbose=False))
        else:
            self.genome_desc = None

        self.hash_to_name = {}
        self.name_to_temp_path = {}

        self.genome_names = self.get_genome_names()


    def get_genome_names(self):
        def get_names(f):
            d = utils.get_TAB_delimited_file_as_dictionary(f, expected_fields=['name'], indexing_field=-1) if f else {}
            return [line['name'] for line in d.values()]

        names = {
            '--fasta-text-file': get_names(self.fasta_txt),
            '--internal-genomes': get_names(self.internal_genomes),
            '--external-genomes': get_names(self.external_genomes),
        }

        for source1, source2 in combinations(names, 2):
            names_in_both = [n for n in names[source1] if n in names[source2]]
            if len(names_in_both):
                raise ConfigError("Ok, so you provided %s and %s as sequence sources, but some names from these sources are shared\
                                   so anvi'o doesn't know how these names should be treated. Here is the list of names that are shared\
                                   by both: [%s]" % (source1, source2, ', '.join([str(n) for n in names_in_both])))

        self.genome_names = []
        for _, names in names.items():
            self.genome_names += names

        return set(self.genome_names)


    def get_fasta_sequences_dir(self):
        if self.genome_desc:
            self.genome_desc.load_genomes_descriptions(skip_functions=True)

        temp_dir,\
        hash_to_name,\
        genome_names,\
        name_to_temp_path = utils.create_fasta_dir_from_sequence_sources(self.genome_desc, self.fasta_txt)

        self.hash_to_name = hash_to_name
        self.genome_names = genome_names
        self.name_to_temp_path = name_to_temp_path
        return temp_dir


    def restore_names_in_dict(self, input_dict):
        """
        Takes dictionary that contains hashes as keys
        and replaces it back to genome names using conversion_dict.

        If value is dict, it calls itself.
        """
        new_dict = {}
        for key, value in input_dict.items():
            if isinstance(value, dict):
                value = self.restore_names_in_dict(value)

            if key in self.hash_to_name:
                new_dict[self.hash_to_name[key]] = value
            else:
                new_dict[key] = value

        return new_dict



class ANI(GenomeDistance):
    def __init__(self, args):
        self.args = args
        self.results = {}

        GenomeDistance.__init__(self, args)

        self.args.quiet = True
        self.program = pyani.PyANI(self.args)

        A = lambda x, t: t(args.__dict__[x]) if x in args.__dict__ else None
        null = lambda x: x
        self.min_alignment_fraction = A('min_alignment_fraction', null)
        self.min_full_percent_identity = A('min_full_percent_identity', null)
        self.significant_alignment_length = A('significant_alignment_length', null)


    def decouple_weak_associations(self):
        """
        potentially modifies results dict using any of:
            {self.min_alignment_fraction, self.significant_alignment_length, self.min_full_percent_identity}
        """
        # in this list we will keep the tuples of genome-genome associations
        # that need to be set to zero in all result dicts:
        genome_hits_to_zero = []
        num_anvio_will_remove_via_full_percent_identity = 0
        num_anvio_wants_to_remove_via_alignment_fraction = 0
        num_saved_by_significant_length_param = 0

        if self.min_full_percent_identity:
            p = self.results.get('full_percentage_identity')
            if not p:
                raise ConfigError("You asked anvi'o to remove weak hits through the --min-full-percent-identity\
                                   parameter, but the results dictionary does not contain any information about\
                                   full percentage identity :/ These are the items anvi'o found instead: '%s'. Please let a\
                                   developer know about this if this doesn't make any sense." % (', '.join(self.results.keys())))

            for g1 in p:
                for g2 in p:
                    if g1 == g2:
                        continue

                    if float(p[g1][g2]) < self.min_full_percent_identity/100 or float(p[g2][g1]) < self.min_full_percent_identity/100:
                        num_anvio_will_remove_via_full_percent_identity += 1
                        genome_hits_to_zero.append((g1, g2), )

            if len(genome_hits_to_zero):
                g1, g2 = genome_hits_to_zero[0]

                run.warning("THIS IS VERY IMPORTANT! You asked anvi'o to remove any hits between\
                             two genomes if they had a full percent identity less than '%.2f'. Anvi'o found %d\
                             such instances between the pairwise comparisons of your %d genomes, and is about\
                             to set all ANI scores between these instances to 0. For instance, one of your \
                             genomes, '%s', had a full percentage identity of %.3f relative to '%s',\
                             another one of your genomes, which is below your threshold, and so the\
                             ANI scores will be ignored (set to 0) for all downstream\
                             reports you will find in anvi'o tables and visualizations. Anvi'o\
                             kindly invites you to carefully think about potential implications of\
                             discarding hits based on an arbitrary alignment fraction, but does not\
                             judge you because it is not perfect either." % (self.min_full_percent_identity/100,
                                                                             num_anvio_will_remove_via_full_percent_identity,
                                                                             len(p), g1, float(p[g1][g2]), g2))

        if self.min_alignment_fraction:
            if 'alignment_coverage' not in self.results:
                raise ConfigError("You asked anvi'o to remove weak hits through the --min-alignment-fraction\
                                   parameter, but the results dictionary does not contain any information about\
                                   alignment fractions :/ These are the items anvi'o found instead: '%s'. Please let a\
                                   developer know about this if this doesn't make any sense." % (', '.join(self.results.keys())))

            if self.significant_alignment_length is not None and 'alignment_lengths' not in self.results:
                raise ConfigError("The pyANI results do not contain any alignment lengths data. Perhaps the method you\
                                   used for pyANI does not produce such data. Well. That's OK. But then you can't use the\
                                   --significant-alignment-length parameter :/")

            d = self.results['alignment_coverage']
            l = self.results['alignment_lengths']

            for g1 in d:
                for g2 in d:
                    if g1 == g2:
                        continue

                    if float(d[g1][g2]) < self.min_alignment_fraction or float(d[g2][g1]) < self.min_alignment_fraction:
                        num_anvio_wants_to_remove_via_alignment_fraction += 1

                        if self.significant_alignment_length and min(float(l[g1][g2]), float(l[g2][g1])) > self.significant_alignment_length:
                            num_saved_by_significant_length_param += 1
                            continue
                        else:
                            genome_hits_to_zero.append((g1, g2), )

            if num_anvio_wants_to_remove_via_alignment_fraction - num_saved_by_significant_length_param > 0:
                g1, g2 = genome_hits_to_zero[num_anvio_will_remove_via_full_percent_identity]

                if num_saved_by_significant_length_param:
                    additional_msg = "By the way, anvi'o saved %d weak hits becasue they were longer than the length of %d nts you\
                                      specified using the --significant-alignment-length parameter. " % \
                                            (num_saved_by_significant_length_param, self.significant_alignment_length)
                else:
                    additional_msg = ""

                run.warning("THIS IS VERY IMPORTANT! You asked anvi'o to remove any hits between two genomes if the hit\
                             was produced by a weak alignment (which you defined as alignment fraction less than '%.2f'). Anvi'o\
                             found %d such instances between the pairwise comparisons of your %d genomes, and is about\
                             to set all ANI scores between these instances to 0. For instance, one of your genomes, '%s',\
                             was %.3f identical to '%s', another one of your genomes, but the aligned fraction of %s to %s was only %.3f\
                             and was below your threshold, and so the ANI scores will be ignored (set to 0) for all downstream\
                             reports you will find in anvi'o tables and visualizations. %sAnvi'o kindly invites you\
                             to carefully think about potential implications of discarding hits based on an arbitrary alignment\
                             fraction, but does not judge you because it is not perfect either." % \
                                                    (self.min_alignment_fraction,
                                                     num_anvio_wants_to_remove_via_alignment_fraction,
                                                     len(d), g1, float(self.results['percentage_identity'][g1][g2]), g2, g1, g2,
                                                     float(self.results['alignment_coverage'][g1][g2]), additional_msg))

            elif num_saved_by_significant_length_param:
                 run.warning("THIS IS VERY IMPORTANT! You asked anvi'o to remove any hits between two genomes if the hit\
                              was produced by a weak alignment (which you defined as an alignment fraction less\
                              than '%.2f'). Anvi'o found %d such instances between the pairwise\
                              comparisons of your %d genomes, but the --significant-alignment-length parameter\
                              saved them all, because each one of them were longer than %d nts. So your filters kinda cancelled\
                              each other out. Just so you know." % \
                                                    (self.min_alignment_fraction,
                                                     num_anvio_wants_to_remove_via_alignment_fraction, len(d),
                                                     self.significant_alignment_length))

        # time to zero those values out:
        genome_hits_to_zero = set(genome_hits_to_zero)
        for report_name in self.results:
            for g1, g2 in genome_hits_to_zero:
                self.results[report_name][g1][g2] = 0
                self.results[report_name][g2][g1] = 0


    def process(self, temp=None):
        temp_dir = temp if temp else self.get_fasta_sequences_dir()

        self.results = self.program.run_command(temp_dir)
        self.results = self.restore_names_in_dict(self.results)
        self.results = self.compute_additonal_matrices(self.results)
        self.decouple_weak_associations()

        if temp is None:
            shutil.rmtree(temp_dir)


    def compute_additonal_matrices(self, results):
        # full percentage identity
        df = lambda matrix_name: pd.DataFrame(results[matrix_name]).astype(float)
        results['full_percentage_identity'] = (df('percentage_identity') * df('alignment_coverage')).to_dict()

        return results



class SourMash(GenomeDistance):
    def __init__(self, args):
        GenomeDistance.__init__(self, args)

        self.results = {}
        self.program = sourmash.Sourmash(args)
        self.min_distance = args.min_mash_distance if 'min_mash_distance' in vars(args) else 0


    def reformat_results(self, results):
        file_to_name = {}
        lines = list(results.keys())
        files = list(results[lines[0]].keys())

        for genome_fasta_path in files:
            genome_fasta_hash = genome_fasta_path[::-1].split(".")[1].split("/")[0][::-1]
            file_to_name[genome_fasta_path] = self.hash_to_name[genome_fasta_hash]

        reformatted_results = {}
        for num, file1 in enumerate(files):
            genome_name_1 = file_to_name[file1]
            reformatted_results[genome_name_1] = {}
            key = lines[num]

            for file2 in files:
                genome_name_2 = file_to_name[file2]
                val = float(results[key][file2])
                reformatted_results[genome_name_1][genome_name_2] = val if val >= self.min_distance else 0

        return reformatted_results


    def process(self, temp=None):
        temp_dir = temp if temp else self.get_fasta_sequences_dir()

        self.results['mash_distance'] = self.program.process(temp_dir, self.name_to_temp_path.values())
        self.results['mash_distance'] = self.reformat_results(self.results['mash_distance'])

        if temp is None:
            shutil.rmtree(temp_dir)

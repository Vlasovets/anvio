#!/usr/bin/env python
# -*- coding: utf-8

import os
import random
import pandas as pd

import anvio
import anvio.terminal as terminal
import anvio.constants as constants
import anvio.filesnpaths as filesnpaths

from anvio.errors import ConfigError
from anvio.parsers.base import Parser
from anvio.parsers.base import TaxonomyHelper


__author__ = "Developers of anvi'o (see AUTHORS.txt)"
__copyright__ = "Copyleft 2015-2018, the Meren Lab (http://merenlab.org/)"
__credits__ = []
__license__ = "GPL 3.0"
__version__ = anvio.__version__
__maintainer__ = "A. Murat Eren"
__email__ = "a.murat.eren@gmail.com"


class Agnostos(Parser):
    def __init__(self, input_file_paths, run=terminal.Run(), progress=terminal.Progress()):
        self.run = run
        self.progress = progress
        self.just_do_it = False

        self.input_file_path = input_file_paths[0]
        files_expected = {'agnostos_output': self.input_file_path}

        files_structure = {'agnostos_output':
                                {'col_names': ['cl_name', 'gene', 'contig', 'gene_x_contig', 'db', 'cl_size', 'category', 'is.HQ', 'is.LS', 'lowest_rank', 'lowest_level', 'mg_project', 'norfs', 'coverage', 'niche_breadth_sign', 'observed', 'mean_proportion', 'pfam', 'gene_callers_id'],
                                 'col_mapping': [str, str, str, int, str, int, str, str, str, str, str, str, int, float, str, float, float, str, int],
                                 'separator': '\t'},
                            }

        # Parser.__init__(self, 'agnostos', input_file_paths, files_expected, files_structure)


    def get_dict(self):
        filesnpaths.is_file_exists(self.input_file_path)

        self.progress.new('Importing Agnostos clustering into contigs')
        self.progress.update('...')

        # Parse Agnostos output to make functions_dict
        df = pd.read_csv(self.input_file_path, sep="\t", header=0)
        df['source'] = "Agnostos"
        df['e_value'] = 0
        df_subset = df[["gene_callers_id", "source", "cl_name", "db", "e_value"]]
        df_subset.rename(columns = {'cl_name':'accession'}, inplace = True)
        df_subset.rename(columns = {'db':'function'}, inplace = True)
        d = df_subset.to_dict(orient='index')

        return d
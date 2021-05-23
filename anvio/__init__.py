# -*- coding: utf-8
# pylint: disable=line-too-long

"""Lots of under-the-rug, operational garbage in here. Run. Run away."""

import os
import sys
import json
import copy
import platform

from tabulate import tabulate

# yes, this library is imported but never used, but don't remove it
# unless you want to explode `bottle`:
import pkg_resources

anvio_version = '7-dev'
anvio_codename = 'hope' # after Hope E. Hopps, https://sivb.org/awards/student-awards/hope-e-hopps-award.html
                        # see the release notes for details: https://github.com/merenlab/anvio/releases/tag/v7

anvio_version_for_help_docs = "main" if anvio_version.endswith('dev') else anvio_version

DEBUG = '--debug' in sys.argv
FORCE = '--force' in sys.argv
QUIET = '--quiet' in sys.argv
NO_PROGRESS = '--no-progress' in sys.argv
AS_MARKDOWN = '--as-markdown' in sys.argv
FIX_SAD_TABLES = '--fix-sad-tables' in sys.argv
DOCS_PATH = os.path.join(os.path.dirname(__file__), 'docs')
TMP_DIR = None

# if the user wants to use a non-default tmp directory, we set it here
if '--tmp-dir' in sys.argv:
    try:
        idx = sys.argv.index('--tmp-dir')
        TMP_DIR = os.path.abspath(sys.argv[idx+1])

        if not os.path.exists(TMP_DIR):
            parent_dir = os.path.dirname(TMP_DIR)
            if os.access(parent_dir, os.W_OK):
                os.makedirs(TMP_DIR)
            else:
                raise OSError(f"You do not have permission to generate a directory in '{parent_dir}'")
        if not os.path.isdir(TMP_DIR):
            raise OSError(f"The path provided to --tmp-dir, {TMP_DIR}, is not a directory...")
        if not os.access(TMP_DIR, os.W_OK):
            raise OSError(f"You do not have permission to generate files in '{TMP_DIR}'")

        os.environ['TMPDIR'] = TMP_DIR
    except Exception as e:
        print("OSError: ", e)
        sys.exit()

def P(d, dont_exit=False):
    """Poor man's debug output printer during debugging."""

    print(json.dumps(d, indent=2))

    if not dont_exit:
        sys.exit()


def TABULATE(table, header, numalign="right", max_width=0):
    """Encoding-safe `tabulate`"""

    tablefmt = "fancy_grid" if sys.stdout.encoding == "UTF-8" else "grid"
    table = tabulate(table, headers=header, tablefmt=tablefmt, numalign=numalign)

    if max_width:
        # let's don't print everything if things need to be cut.
        prefix = " // "
        lines_in_table = table.split('\n')
        if len(lines_in_table[0]) + len(prefix) + 2 > max_width:
            table = '\n'.join([l[:max_width - len(prefix)] + prefix + l[-2:] for l in lines_in_table])

    print(table)


# Make sure the Python environment hasn't changed since the installation (happens more often than you'd think
# on systems working with multiple Python installations that are managed through modules):
try:
    if sys.version_info.major != 3 or sys.version_info.minor < 5:
        sys.stderr.write("Sad face :( Your active Python version is %s, but anvi'o only works with Python version 3.5.0 or later.\n" % (platform.python_version()))
        sys.exit(-1)
except Exception:
    sys.stderr.write("(anvi'o failed to learn about your Python version, but it will pretend as if nothing happened)\n\n")


import anvio.constants as constants


# a comprehensive arguments dictionary that provides easy access from various programs that interface anvi'o modules:
D = {
    'profile-db': (
            ['-p', '--profile-db'],
            {'metavar': "PROFILE_DB",
             'required': True,
             'help': "Anvi'o profile database"}
                ),
    'genes-db': (
            ['--genes-db'],
            {'metavar': "GENES_DB",
             'required': True,
             'help': "Anvi'o genes database"}
                ),
    'pan-db': (
            ['-p', '--pan-db'],
            {'metavar': "PAN_DB",
             'required': True,
             'help': "Anvi'o pan database"}
                ),
    'pan-or-profile-db': (
            ['-p', '--pan-or-profile-db'],
            {'metavar': "PAN_OR_PROFILE_DB",
             'required': True,
             'help': "Anvi'o pan or profile database (and even genes database in appropriate contexts)."}
                ),
    'genomes-storage': (
            ['-g', '--genomes-storage'],
            {'metavar': "GENOMES_STORAGE",
             'required': False,
             'help': "Anvi'o genomes storage file"}
                ),
    'structure-db': (
            ['-s', '--structure-db'],
            {'metavar': "STRUCTURE_DB",
             'required': True,
             'help': "Anvi'o structure database."}
                ),
    'only-if-structure': (
            ['--only-if-structure'],
            {'default': False,
             'action': 'store_true',
             'help': "If provided, your genes of interest will be further subset to only include "
                     "genes with structures in your structure database, and therefore must be supplied in "
                     "conjunction with a structure database, i.e. `-s <your_structure_database>`. If you did "
                     "not specify genes of interest, ALL genes will be subset to those that have "
                     "structures."}
                ),
    'genomes-names': (
            ['-G', '--genome-names'],
            {'metavar': "GENOME_NAMES",
             'required': False,
             'help': "Genome names to 'focus'. You can use this parameter to limit the genomes included in your analysis. "
                     "You can provide these names as a comma-separated list of names, or you can put them in a file, "
                     "where you have a single genome name in each line, and provide the file path."}
                ),
    'blank-profile': (
            ['--blank-profile'],
            {'default': False,
             'action': 'store_true',
             'help': "If you only have contig sequences, but no mapping data (i.e., you found a genome and would like to "
                     "take a look from it), this flag will become very handy. After creating a contigs database for your "
                     "contigs, you can create a blank anvi'o profile database to use anvi'o interactive "
                     "interface with that contigs database without any mapping data."}
                ),
    'contigs-db': (
            ['-c', '--contigs-db'],
            {'metavar': 'CONTIGS_DB',
             'required': True,
             'help': "Anvi'o contigs database generated by 'anvi-gen-contigs-database'"}
                ),
    'runinfo': (
            ['-r', '--runinfo'],
            {'metavar': 'RUNINFO_PATH',
             'required': True,
             'help': "Anvi'o runinfo file path."}
                ),
    'description': (
            ['--description'],
            {'metavar': 'TEXT_FILE',
             'required': False,
             'help': "A plain text file that contains some description about the project. You can use Markdown syntax. "
                     "The description text will be rendered and shown in all relevant interfaces, including the "
                     "anvi'o interactive interface, or anvi'o summary outputs."}
                ),

    'additional-view': (
            ['-V', '--additional-view'],
            {'metavar': 'ADDITIONAL_VIEW',
             'help': "A TAB-delimited file for an additional view to be used in the interface. This "
                     "file should contain all split names, and values for each of them in all "
                     "samples. Each column in this file must correspond to a sample name. Content "
                     "of this file will be called 'user_view', which will be available as a new item "
                     "in the 'views' combo box in the interface"}
                ),
    'fasta-file': (
            ['-f', '--fasta-file'],
            {'metavar': 'FASTA',
             'help': "A FASTA-formatted input file"}
                ),
    'dna-sequence': (
            ['--dna-sequence'],
            {'metavar': 'FASTA',
             'help': "A FASTA-formatted input file"}
                ),
    'fasta-text-file': (
            ['-f', '--fasta-text-file'],
            {'metavar': 'FASTA_TEXT_FILE',
            'dest': 'fasta_text_file',
            'help': "A two-column TAB-delimited file that lists multiple FASTA files to import "
                    "for analysis. If using for `anvi-dereplicate-genomes` or `anvi-compute-distance`, "
                    "each FASTA is assumed to be a genome. The first item in the header line "
                    "should read 'name', and the second item should read 'path'. Each line "
                    "in the field should describe a single entry, where the first column is "
                    "the name of the FASTA file or corresponding sequence, and the second column "
                    "is the path to the FASTA file itself."}
                ),
    'layers-information-file': (
            ['-D', '--layers-information-file'],
            {'metavar': 'FILE',
             'help': "A TAB-delimited file with information about layers in your dataset. Each row in this "
                     "file must correspond to a sample name. Each column must contain a unique attribute. "
                     "Please refer to the documentation to learn more about the structure and purpose of "
                     "this file."}
                ),
    'layers-order-file': (
            ['-R', '--layers-order-file'],
            {'metavar': 'FILE',
             'help': "A TAB-delimited file with three columns: 'attribute', 'basic', 'newick'. For each attribute, "
                     "the order of samples must be defined either in the 'basic' form or via a 'newick'-formatted "
                     "tree structure that describes the organization of each sample. Anvi'o will look for a "
                     "comma-separated list of sample names for the 'basic' form. Please refer to the online docs "
                     "for more info. Also you shouldn't hesitate to try to find the right file format until you get "
                     "it working. There are stringent checks on this file, and you will not break anything while trying!."}
                ),
    'split-length': (
            ['-L', '--split-length'],
            {'metavar': 'INT',
             'default': 20000,
             'type': int,
             'help': "Anvi'o splits very long contigs into smaller pieces, without actually splitting them for real. These "
                     "'virtual' splits improve the efficacy of the visualization step, and changing the split size gives "
                     "freedom to the user to adjust the resolution of their display when necessary. The default value is "
                     "(%(default)d). If you are planning to use your contigs database for metagenomic binning, we advise you "
                     "to not go below 10,000 (since the lower the split size is, the more items to show in the display, and "
                     "decreasing the split size does not really help much to binning). But if you are thinking about using this "
                     "parameter for ad hoc investigations other than binning, you should ignore our advice, and set the split "
                     "size as low as you want. If you do not want your contigs to be split, you can set the split size to '0' "
                     "or any other negative integer (lots of unnecessary freedom here, enjoy!)."}
                ),
    'kmer-size': (
            ['-K', '--kmer-size'],
            {'metavar': 'INT',
             'default': 4,
             'type': int,
             'help': "K-mer size for k-mer frequency calculations. The default k-mer size for composition-based "
                     "analyses is 4, historically. Although tetra-nucleotide frequencies seem to offer the "
                     "the sweet spot of sensitivity, information density, and manageable number of dimensions "
                     "for clustering approaches, you are welcome to experiment (but maybe you should leave "
                     "it as is for your first set of analyses)."}
                ),
    'prodigal-translation-table': (
            ['--prodigal-translation-table'],
            {'metavar': 'INT',
             'default': None,
             'help': "This is a parameter to pass to the Prodigal for a specific translation table. This parameter "
                     "corresponds to the parameter `-g` in Prodigal, the default value of which is 11 (so if you do "
                     "not set anything, it will be set to 11 in Prodigal runtime. Please refer to the Prodigal "
                     "documentation to determine what is the right translation table for you if you think you need "
                     "it.)"}
                ),

    'skip-gene-calling': (
            ['--skip-gene-calling'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, generating an anvi'o contigs database includes the identification of open reading "
                     "frames in contigs by running a bacterial gene caller. Declaring this flag will by-pass that "
                     "process. If you prefer, you can later import your own gene calling results into the database."}
                ),
    'remove-partial-hits': (
            ['--remove-partial-hits'],
            {'default': False,
             'action': 'store_true',
             'help': "By default anvi'o will return hits even if they are partial. Declaring this flag will make "
                     "anvi'o filter all hits that are partial. Partial hits are hits in which you asked for n1 "
                     "genes before and n2 genes after the gene that matched the search criteria but the search "
                     "hits the end of the contig before finding the number of genes that you asked."}
            ),
    'never-reverse-complement': (
            ['--never-reverse-complement'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, if a gene that is found by the search criteria is reverse in it's direction, "
                     "then the sequence of the entire locus is reversed before it is saved to the output. "
                     "If you wish to prevent this behavior then use the flag --never-reverse-complement.",}
             ),
    'zeros-are-outliers': (
            ['--zeros-are-outliers'],
            {'default': False,
             'action': 'store_true',
             'help': "If you want all zero coverage positions to be treated like outliers "
                     "then use this flag. The reason to treat zero coverage as outliers "
                     "is because when mapping reads to a reference we could get many zero "
                     "positions due to accessory genes. These positions then skew the average "
                     "values that we compute."}
            ),
    'outliers-threshold': (
            ['--outliers-threshold'],
            {'default': 1.5,
             'type': float,
             'metavar': 'NUM',
             'help': "Threshold to use for the outlier detection. The default value is '%(default).1f'. "
                     "Absolute deviation around the median is used. To read more about the method please "
                     "refer to: 'How to Detect and Handle Outliers' by Boris Iglewicz and David Hoaglin "
                     "(doi:10.1016/j.jesp.2013.03.013)."}
            ),
    'external-gene-calls': (
            ['--external-gene-calls'],
            {'metavar': 'GENE-CALLS',
             'help': "A TAB-delimited file to define external gene calls. The file must have these columns: 'gene_callers_id' "
                     "(a unique integer number for each gene call, start from 1), 'contig' (the contig name the gene call is found), "
                     "'start' (start position, integer), 'stop' (stop position, integer), 'direction' (the direction of the gene open reading "
                     "frame; can be 'f' or 'r'), 'partial' (whether it is a complete gene call, or a partial one; must be 1 for partial "
                     "calls, and 0 for complete calls), 'call_type' (1 if it is coding, 2 if it is noncoding, or 3 if it is unknown (only gene "
                     "calls with call_type = 1 will have amino acid sequences translated)), 'source' (the gene caller), "
                     "and 'version' (the version of the gene caller, i.e., v2.6.7 or v1.0). An additional 'optional' column is 'aa_sequence'"
                     " to explicitly define the amino acid seqeuence of a gene call so anvi'o does not attempt to translate the "
                     "DNA sequence itself. An EXAMPLE FILE (with the optional 'aa_sequence' column (so feel free to take it out "
                     "for your own case)) can be found at the URL https://bit.ly/2qEEHuQ. If you are providing external gene calls, "
                     "please also see the flag `--skip-predict-frame`."}
                ),
    'external-genomes': (
            ['-e', '--external-genomes'],
            {'metavar': 'FILE_PATH',
             'help': "A two-column TAB-delimited flat text file that lists anvi'o contigs databases. The first item "
                     "in the header line should read 'name', and the second should read 'contigs_db_path'. Each line in the "
                     "file should describe a single entry, where the first column is the name of the genome (or MAG), and "
                     "the second column is the anvi'o contigs database generated for this genome."}
                ),
    'internal-genomes': (
            ['-i', '--internal-genomes'],
            {'metavar': 'FILE_PATH',
             'help': "A five-column TAB-delimited flat text file. The header line must contain these columns: 'name', 'bin_id', "
                     "'collection_id', 'profile_db_path', 'contigs_db_path'. Each line should list a single entry, where 'name' "
                     "can be any name to describe the anvi'o bin identified as 'bin_id' that is stored in a collection."}
                ),
    'skip-checking-genome-hashes': (
            ['--skip-checking-genome-hashes'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you would like anvi'o to skip checking genome hashes. This is only relevant if you may have "
                     "genomes in your internal or external genomes files that have identical sequences with different names AND if "
                     "you are OK with it. You may be OK with it, for instance, if you are using `anvi-dereplicate-genomes` program "
                     "to dereplicate genomes desribed in multiple collections in an anvi'o profile database that may be describing "
                     "the same genome multiple times (see https://github.com/merenlab/anvio/issues/1397 for a case)."}
                ),
    'metagenomes': (
            ['-M', '--metagenomes'],
            {'metavar': 'FILE_PATH',
             'help': "A two-column TAB-delimited flat text file. The header line must contain these columns: 'name', "
                     "'contigs_db_path', and 'profile_db_path'. Each line should list a single entry, where 'name' "
                     "can be any name to describe the metagenome stored in the anvi'o contigs database. In this "
                     "context, the anvi'o profiles associated with contigs database must be SINGLE PROFILES, as in "
                     "generated by the program `anvi-profile` and not `anvi-merge`."}
                ),
    'gene-caller': (
            ['--gene-caller'],
            {'metavar': 'GENE-CALLER',
             'help': "The gene caller to utilize. Anvi'o supports multiple gene callers, and some operations (including this one) "
                     "requires an explicit mentioning of which one to use. The default is '%s', but it will not be enough if you "
                     "if you were a rebel and have used `--external-gene-callers` or something." % constants.default_gene_caller}
                ),
    'list-gene-callers': (
            ['--list-gene-callers'],
            {'default': False,
             'action': 'store_true',
             'help': "List available gene callers in the contigs database and quit."}
                ),
    'ignore-internal-stop-codons': (
            ['--ignore-internal-stop-codons'],
            {'default': False,
             'action': 'store_true',
             'help': "This is only relevant when you have an external gene calls file. If anvi'o figures out that your custom gene calls "
                     "result in amino acid sequences with stop codons in the middle, it will complain about it. You can use this flag "
                     "to tell anvi'o to don't check for internal stop codons, Even though this shouldn't happen in theory, we understand "
                     "that it almost always does. In these cases, anvi'o understands that sometimes we don't want to care, and will "
                     "not judge you. Instead, it will replace every stop codon residue in the amino acid sequence with an 'X' character. "
                     "Please let us know if you used this and things failed, so we can tell you that you shouldn't have really used it "
                     "if you didn't like failures at the first place (smiley)."}
                ),
    'skip-predict-frame': (
            ['--skip-predict-frame'],
            {'default': False,
             'action': 'store_true',
             'help': "When you have provide an external gene calls file, anvi'o will predict the correct frame for gene calls as best as it can by "
                     "using a previously-generated Markov model that is trained using the uniprot50 database (see this for details: "
                     "https://github.com/merenlab/anvio/pull/1428), UNLESS there is an `aa_sequence` entry for a given gene call in the external "
                     "gene calls file. Please note that PREDICTING FRAMES MAY CHANGE START/STOP POSITIONS OF YOUR GENE CALLS SLIGHTLY, if "
                     "those that are in the external gene calls file are not describing proper gene calls according to the model. "
                     "If you use this flag, anvi'o will not rely on any model and will attempt to translate your DNA sequences by solely "
                     "relying upon start/stop positions in the file, but it will complain about sequences start/stop positions of which are "
                     "not divisible by 3."}
                ),
    'get-samples-stats-only': (
            ['--get-samples-stats-only'],
            {'default': False,
             'action': 'store_true',
             'help': "If you only wish to get statistics regarding the occurrence of bins in samples, then use this flag. "
                     "Especially when dealing with many samples or large genomes, gene stats could be a long time to compute. "
                     "By using this flag you could save a lot of computation time."}
                ),
    'gen-figures': (
            ['--gen-figures'],
            {'default': False,
             'action': 'store_true',
             'help': "For those of you who wish to dig deeper, a collection of figures could be created to allow "
                     "you to get insight into how the classification was generated. This is especially useful to "
                     "identify cases in which you shouldn't trust the classification (for example due to a large "
                     "number of outliers). NOTICE: if you ask anvi'o to generate these figures then it will "
                     "significantly extend the execution time. To learn about which figures are created and what "
                     "they mean, contact your nearest anvi'o developer, because currently it is a well-hidden secret."}
                ),
    'skip-SNV-profiling': (
            ['--skip-SNV-profiling'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, anvi'o characterizes single-nucleotide variation in each sample. The use of this flag "
                     "will instruct profiler to skip that step. Please remember that parameters and flags must be "
                     "identical between different profiles using the same contigs database for them to merge properly."}
                ),
    'skip-INDEL-profiling': (
            ['--skip-INDEL-profiling'],
            {'default': False,
             'action': 'store_true',
             'help': "The alignment of a read to a reference genome/sequence can be imperfect, such that the read exhibits "
                     "insertions or deletions relative to the reference. Anvi'o normally stores this information in the "
                     "profile database since the time taken and extra storage do not amount to much, but if you insist on not "
                     "having this information, you can skip storing this information by providing this flag. Note: If "
                     "--skip-SNV-profiling is provided, --skip-INDEL-profiling will automatically be enforced."}
                ),
    'return-AA-frequencies-instead': (
            ['--return-AA-frequencies-instead'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, anvi'o will return codon frequencies (as the name suggests), but you can ask for amino "
                     "acid frequencies instead, simply because you always need more data and more stuff. You're lucky "
                     "this time, but is there an end to this? Will you ever be satisfied with what you have? "
                     "Anvi'o needs answers."}
                ),
    'profile-SCVs': (
            ['--profile-SCVs'],
            {'default': False,
             'action': 'store_true',
             'help': "Anvi'o can perform accurate characterization of codon frequencies in genes during profiling. While having "
                     "codon frequencies opens doors to powerful evolutionary insights in downstream analyses, due to its "
                     "computational complexity, this feature comes 'off' by default. Using this flag you can rise against the "
                     "authority, as you always should, and make anvi'o profile codons."}
                ),
    'drop-previous-annotations': (
            ['--drop-previous-annotations'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you want anvi'o to remove ALL previous functional annotations for your genes, "
                     "and then import the new data. The default behavior will add any annotation source into the db "
                     "incrementally unless there are already annotations from this source. In which case, it will first "
                     "remove previous annotations for that source only (i.e., if source X is both in the db and in the "
                     "incoming annotations data, it will replace the content of source X in the db)."}
                ),
    'skip-mindful-splitting': (
            ['--skip-mindful-splitting'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, anvi'o attempts to prevent soft-splitting large contigs by cutting proper gene calls "
                     "to make sure a single gene is not broken into multiple splits. This requires a careful "
                     "examination of where genes start and end, and to find best locations to split contigs with respect "
                     "to this information. So, when the user asks for a split size of, say, 1,000, it serves as a "
                     "mere suggestion. When this flag is used, anvi'o does what the user wants and creates splits at "
                     "desired lengths (although some functionality may become unavailable for the projects that rely on "
                     "a contigs database that is initiated this way)."}
                ),
    'db-variant': (
            ['--db-variant'],
            {'metavar': 'VARIANT',
             'required': False,
             'default': 'unknown',
             'help': "A free-form text variable to associate a database with a variant for power users and/or programmers "
                     "Please leave this blank unless you are certain that you need to set a db variant since it may influence "
                     "downstream processes. In an ideal world a varainat would be a single-word, without any capitalized letters "
                     "or special characters."}
                ),
    'contigs-fasta': (
            ['-f', '--contigs-fasta'],
            {'metavar': 'FASTA',
             'required': True,
             'help': "The FASTA file that contains reference sequences you mapped your samples against. This "
                     "could be a reference genome, or contigs from your assembler. Contig names in this file "
                     "must match to those in other input files. If there is a problem anvi'o will gracefully "
                     "complain about it."}
                ),
    'view-data': (
            ['-d', '--view-data'],
            {'metavar': 'VIEW_DATA',
             'help': "A TAB-delimited file for view data"}
                ),
    'tree': (
            ['-t', '--tree'],
            {'metavar': 'NEWICK',
             'help': "NEWICK formatted tree structure"}
                ),
    'items-order': (
            ['--items-order'],
            {'metavar': 'FLAT_FILE',
             'help': "A flat file that contains the order of items you wish the display using the interactive interface. You "
                     "may want to use this if you have a specific order of items in your mind, and do not want to display a "
                     "tree in the middle (or simply you don't have one). The file format is simple: each line should have an "
                     "item name, and there should be no header."}
                ),
    'additional-layers': (
            ['-A', '--additional-layers'],
            {'metavar': 'ADDITIONAL_LAYERS',
             'help': "A TAB-delimited file for additional layers for splits. The first column of this file "
                     "must be split names, and the remaining columns should be unique attributes. "
                     "The file does not need to contain all split names, or values for each split in "
                     "every column. Anvi'o will try to deal with missing data nicely. Each column in this "
                     "file will be visualized as a new layer in the tree."}
                ),
    'target-data-group': (
            ['-D', '--target-data-group'],
            {'metavar': 'NAME',
             'default': None,
             'help': "Data group to focus. Anvi'o misc data tables support associating a set of data keys "
                     "with a data group. If you have no idea what this is, then probably you don't need it, "
                     "and anvi'o will take care of you. Note: this flag is IRRELEVANT if you are working with "
                     "additional order data tables."}
                ),
    'target-data-table': (
            ['-t', '--target-data-table'],
            {'metavar': 'NAME',
             'help': "The target table is the table you are interested in accessing. Currently it can be 'items','layers', or "
                     "'layer_orders'. Please see most up-to-date online documentation for more information."}
                ),
    'view': (
            ['--view'],
            {'metavar': 'NAME',
             'help': "Start the interface with a pre-selected view. To see a list of available views, "
                     "use --show-views flag."}
                ),
    'category-variable': (
            ['--category-variable'],
            {'default': None,
             'metavar': 'CATEGORY',
             'help': "The additional layers data variable name that divides layers into multiple categories."}
                ),
    'include-ungrouped': (
            ['--include-ungrouped'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you want anvi'o to include genomes/samples with no group in the analysis. (For pangenomes, this means "
                     "the genome has no value set for the category variable which you specified using --category-variable. "
                     "For modules, this means the sample has no group specified in the groups-txt file. And for regular 'ol "
                     "genomes, this means the genome has nothing in the 'group' column of the input file). By default all "
                     "variables with no value will be ignored, but if you apply this flag, they will instead be considered as "
                     "a single group (called 'UNGROUPED' when performing the statistical analysis."}
                ),
    'include-samples-missing-from-groups-txt': (
            ['--include-samples-missing-from-groups-txt'],
            {'default': False,
            'action': 'store_true',
            'help': "Sometimes, you might have some sample names in your modules-txt file that you did not include in the groups-txt file. "
                    "This is fine. By default, we will ignore those samples because they do not have a group. But if you use this flag, then "
                    "instead those samples will be included in a group called 'UNGROUPED'. Be cautious when using this flag in combination with "
                    "the --include-ungrouped flag (which also sticks samples without groups into the 'UNGROUPED' group) so that you don't accidentally "
                    "group together samples that are not supposed to be friends."}
                ),
    'functional-occurrence-table-output': (
            ['-F', '--functional-occurrence-table-output'],
            {'metavar': 'FILE',
             'default': None,
             'type': str,
             'help': "Saves the occurrence frequency information for functions in genomes in a TAB-delimited format. "
                     "A file name must be provided. To learn more about how the functional occurrence is computed, please "
                     "refer to the tutorial."}
                ),
    'table': (
            ['--table'],
            {'metavar': 'TABLE_NAME',
             'help': "Table name to export."}
                ),
    'fields': (
            ['-f', '--fields'],
            {'metavar': 'FIELD(S)',
             'help': "Fields to report. Use --list-tables parameter with a table name to see available "
                     "fields  You can list fields using this notation: --fields 'field_1, field_2, ... field_N'."}
                ),
    'list': (
            ['-l', '--list'],
            {'default': False,
             'action': 'store_true',
             'help': "Gives a list of tables in a database and quits. If a table is already declared "
                     "this time it lists all the fields in a given table, in case you would to export "
                     "only a specific list of fields from the table using --fields parameter."}
                ),
    'title': (
            ['--title'],
            {'metavar': 'NAME',
             'help': "Title for the interface. If you are working with a RUNINFO dict, the title "
                     "will be determined based on information stored in that file. Regardless, "
                     "you can override that value using this parameter."}
                ),
    'split-hmm-layers': (
            ['--split-hmm-layers'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, this flag tells the interface to split every gene found in HMM "
                     "searches that were performed against non-singlecopy gene HMM profiles into "
                     "their own layer. Please see the documentation for details."}
                ),
    'show-all-layers': (
            ['--show-all-layers'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, this flag tells the interface to show every additional layer even if "
                     "there are no hits. By default, anvi'o doesn't show layers if there are no hits for "
                     "any of your items."}
                ),
    'taxonomic-level': (
            ['--taxonomic-level'],
            {'default': 't_genus',
             'type': str,
             'choices': constants.levels_of_taxonomy,
             'help': "The taxonomic level to use whenever relevant and/or available. The default taxonomic level "
                     "is %(default)s, but if you choose something specific, anvi'o will focus on that whenever "
                     "possible."}
                ),
    'taxonomy-file': (
            ['-t', '--taxonomy-file'],
            {'default': None,
             'type': str,
             'help': "Path to The taxonomy file format tsv containe: "
             "ID\td__domaine;p__phylum;[..];s__genus species"}
                ),
    'metagenome-mode': (
            ['-m', '--metagenome-mode'],
            {'default': False,
             'action': 'store_true',
             'help': "Treat a given contigs database as a metagenome rather than treating it as a single genome."}
                ),
    'scg-name-for-metagenome-mode': (
            ['-S','--scg-name-for-metagenome-mode'],
            {'default': None,
             'type': str,
             'metavar': 'SCG_NAME',
             'help': "When running in metagenome mode, anvi'o automatically chooses the most frequent single-copy "
                     "core gene to estimate the taxonomic composition within a contigs database. If you have a "
                     "different preference you can use this parameter to communicate that."}
                ),
    'anticodon-for-metagenome-mode': (
            ['-S','--anticodon-for-metagenome-mode'],
            {'default': None,
             'type': str,
             'metavar': 'ANTICODON',
             'help': "When running in metagenome mode, anvi'o automatically chooses the most frequent anticodon "
                     "to estimate the taxonomic composition within a contigs database. If you have a "
                     "different preference you can use this parameter to communicate that."}
                ),
    'per-anticodon-output-file': (
            ['--per-anticodon-output-file'],
            {'default': None,
             'type': str,
             'metavar': 'FILE_PATH',
             'help': "A more detailed output file that will describe taxonomy of each anticodon in a single bin. "
                     "When consensus taxonomy is generated per bin or genome, taxonomy for each underlying item "
                     "is not reported. This additional optional output file will elucidate things."}
                ),
    'per-scg-output-file': (
            ['--per-scg-output-file'],
            {'default': None,
             'type': str,
             'metavar': 'FILE_PATH',
             'help': "A more detailed output file that will describe taxonomy of each scg in a single bin. "
                     "When consensus taxonomy is generated per bin or genome, taxonomy for each underlying item "
                     "is not reported. This additional optional output file will elucidate things."}
                ),
    'all-hits-output-file': (
            ['--all-hits-output-file'],
            {'default': None,
             'type': str,
             'metavar': 'FILE_PATH',
             'help': "If this flag is declared, anvi'o will store a comprehensive list of hits that led to the "
                     "determination of the consensus hit per sequence (which is the only piece of information that "
                     "is stored in the contigs database)."}
                ),
    'report-scg-frequencies': (
            ['--report-scg-frequencies'],
            {'default': None,
             'type': str,
             'metavar': 'FILE_PATH',
             'help': "Report SCG frequencies in a TAB-delimited file and quit. This is a great way to decide which "
                     "SCG name to use in metagenome mode (we often wish to use the most frequent SCG to increase the "
                     "detection of taxa)."}
                ),
    'report-anticodon-frequencies': (
            ['--report-anticodon-frequencies'],
            {'default': None,
             'type': str,
             'metavar': 'FILE_PATH',
             'help': "Report anticodon frequencies in a TAB-delimited file and quit. This is a great way to decide which "
                     "anticodon to use in metagenome mode (we often wish to use the most frequent anticodon to increase the "
                     "detection of taxa)."}
                ),
    'simplify-taxonomy-information': (
            ['--simplify-taxonomy-information'],
            {'default': False,
             'action': 'store_true',
             'help': "The taxonomy output may include a large number of names that contain clade-specific code for "
                     "not-yet-characterized taxa. With this flag you can simplify taxon names. This will influence "
                     "all output files and displays as the use of this flag will on-the-fly trim taxonomic levels "
                     "with clade-specific code names."}
                ),
    'compute-scg-coverages': (
            ['--compute-scg-coverages'],
            {'default': False,
             'action': 'store_true',
             'help': "When this flag is declared, anvi'o will go back to the profile database to learn coverage "
                     "statistics of single-copy core genes for which we have taxonomy information."}
                ),
    'compute-anticodon-coverages': (
            ['--compute-anticodon-coverages'],
            {'default': False,
             'action': 'store_true',
             'help': "When this flag is declared, anvi'o will go back to the profile database to learn coverage "
                     "statistics of tRNA genes used for taxonomy."}
                ),
    'update-profile-db-with-taxonomy': (
            ['--update-profile-db-with-taxonomy'],
            {'default': False,
             'action': 'store_true',
             'help': "When anvi'o knows all both taxonomic affiliations and coverages across samples for single-copy "
                     "core genes, it can, in theory add this information to the profile database. With this flag you "
                     "can instruct anvi'o to do that and find information on taxonomy in the `layers` tab of your "
                     "interactive interface."}
                ),
    'taxonomy-database': (
            ['-r', '--taxonomy-database'],
            {'default': None,
             'type': str,
             'metavar': 'PATH',
             'help': "Path to the directory that contains the BLAST databases for single-copy core "
                     "genes. You will almost never need to use this parameter unless you are "
                     "trying something very fancy. But when you do, you can tell anvi'o where "
                     "to look for database files through this parameter."}
                ),
    'scgs-taxonomy-data-dir': (
            ['--scgs-taxonomy-data-dir'],
            {'default': None,
             'type': str,
             'metavar': 'PATH',
             'help': "The directory for SCGs data to be stored (or read from, depending on the context). "
                     "If you leave it as is without specifying anything, anvi'o will set up everything in "
                     "(or try to read things from) a pre-defined default directory. The advantage of using "
                     "the default directory at the time of set up is that every user of anvi'o on a computer "
                     "system will be using a single data directory, but then you may need to run the setup "
                     "program with superuser privileges. If you don't have superuser privileges, then you can "
                     "use this parameter to tell anvi'o the location you wish to use to setup your databases. "
                     "If you are using a program (such as `anvi-run-scg-taxonomy` or `anvi-estimate-scg-taxonomy`) "
                     "you will have to use this parameter to tell those programs where your data are."}
                ),
    'trna-taxonomy-data-dir': (
            ['--trna-taxonomy-data-dir'],
            {'default': None,
             'type': str,
             'metavar': 'PATH',
             'help': "The directory for tRNA taxonomy data to be stored (or read from, depending on the context). "
                     "If you leave it as is without specifying anything, anvi'o will set up everything in "
                     "(or try to read things from) a pre-defined default directory. The advantage of using "
                     "the default directory at the time of set up is that every user of anvi'o on a computer "
                     "system will be using a single data directory, but then you may need to run the setup "
                     "program with superuser privileges. If you don't have superuser privileges, then you can "
                     "use this parameter to tell anvi'o the location you wish to use to setup your databases. "
                     "If you are using a program (such as `anvi-run-trna-taxonomy` or `anvi-estimate-trna-taxonomy`) "
                     "you will have to use this parameter to tell those programs where your data are."}
                ),
    'gtdb-release': (
            ['--gtdb-release'],
            {'default': None,
             'type': str,
             'metavar': 'RELEASE_NUM',
             'help': "If you are particularly intersted an earlier release anvi'o knows about, you can set it here "
                     "Otherwise anvi'o will always use the latest release it knows about."}
                ),
    'reset': (
            ['--reset'],
            {'default': False,
             'action': 'store_true',
             'help': "Remove all the previously stored files and start over. If something is feels wrong "
                     "for some reason and if you believe re-downloading files and setting them up could "
                     "address the issue, this is the flag that will tell anvi'o to act like a real computer "
                     "scientist challenged with a computational problem."}
                ),
    'redo-databases': (
            ['--redo-databases'],
            {'default': False,
             'action': 'store_true',
             'help': "Remove existing databases and re-create them. This can be necessary when versions of "
                     "programs change and databases they create and use become incompatible."}
                ),
    'cog-data-dir': (
            ['--cog-data-dir'],
            {'default': None,
             'type': str,
             'help': "The directory path for your COG setup. Anvi'o will try to use the default path "
                     "if you do not specify anything."}
                ),
    'cog-version': (
            ['--cog-version'],
            {'default': None,
             'type': str,
             'help': "COG version. The default is the latest version, which is COG20, meaning that anvi'o will "
                     "use the NCBI's 2020 release of COGs to setup the database and run it on contigs databases. "
                     "There is also an older version of COGs from 2014. If you would like anvi'o to work with that "
                     "one, please use COG14 as a parameter. On a single computer you can have both, and on a single "
                     "contigs database you can run both. Cool and confusing. The anvi'o way."}
                ),
    'pfam-data-dir': (
            ['--pfam-data-dir'],
            {'default': None,
             'type': str,
             'help': "The directory path for your Pfam setup. Anvi'o will try to use the default path "
                     "if you do not specify anything."}
                ),
    'pdb-database-path': (
            ['--pdb-database-path'],
            {'default': None,
             'type': str,
             'metavar': 'PATH',
             'help': "The path for the PDB database to be stored. "
                     "If you leave it as is without specifying anything, anvi'o will set up everything in "
                     "a pre-defined default directory. The advantage of using "
                     "the default directory at the time of set up is that every user of anvi'o on a computer "
                     "system will be using a single data directory, but then you may need to run the setup "
                     "program with superuser privileges. If you don't have superuser privileges, then you can "
                     "use this parameter to tell anvi'o the location you wish to use to setup your database."}
                ),
    'interacdome-data-dir': (
            ['--interacdome-data-dir'],
            {'default': None,
             'type': str,
             'metavar': 'PATH',
             'help': "The path for the interacdome data to be stored. "
                     "If you leave it as is without specifying anything, anvi'o will set up everything in "
                     "a pre-defined default directory. The advantage of using "
                     "the default directory at the time of set up is that every user of anvi'o on a computer "
                     "system will be using a single data directory, but then you may need to run the setup "
                     "program with superuser privileges. If you don't have superuser privileges, then you can "
                     "use this parameter to tell anvi'o the location you wish to use to setup your data."}
                ),
    'interacdome-dataset': (
            ['--interacdome-dataset'],
            {'default': 'representable',
             'type': str,
             'choices': ['representable', 'confident'],
             'help': "Choose 'representable' to include Pfams that correspond to domain-ligand interactions that had "
                     "nonredundant instances across three or more distinct PDB structures. InteracDome"
                     "authors recommend using this collection to learn more about domain binding properties. Choose "
                     "'confident' to include Pfams that correspond to domain-ligand interactions "
                     "that had nonredundant instances across three or more distinct PDB entries and "
                     "achieved a cross-validated precision of at least 0.5. We recommend using this "
                     "collection to annotate potential ligand-binding positions in protein "
                     "sequences. The default is '%(default)s'."}
                ),
    'kegg-data-dir': (
            ['--kegg-data-dir'],
            {'default': None,
             'type': str,
             'help': "The directory path for your KEGG setup, which will include things like "
                     "KOfam profiles and KEGG MODULE data. Anvi'o will try to use the default path "
                     "if you do not specify anything."}
                ),
    'kegg-archive': (
            ['--kegg-archive'],
            {'default': None,
             'type': str,
             'help': "The path to an archived (.tar.gz) KEGG directory (which you have downloaded from figshare or from "
                     "a collaborator who has a KEGG data directory generated by anvi'o). If you provide this parameter, "
                     "anvi'o will set up the KEGG data directory from the archive you specify rather than downloading "
                     "and setting up our default KEGG archive."}
                ),
    'download-from-kegg': (
            ['-D', '--download-from-kegg'],
            {'default': False,
             'action': 'store_true',
             'help': "This flag is for those people who always need the latest data. You know who you are :) "
                     "By default, this program will set up a snapshot of the KEGG databases, which will be "
                     "dated to the time of the anvi'o release that you are currently working with. The pros of "
                     "this are that the KEGG data will be the same for everyone (which makes sharing your KEGG-annotated "
                     "datasets easy), and you will not have to worry about updating your datasets with new annotations "
                     "every time that KEGG updates. However, KEGG updates regularly, so the con of this is that "
                     "you will not have the most up-to-date version of KEGG for your annotations, metabolism "
                     "estimations, or any other downstream uses of this data. If that is going to be a problem for you, "
                     "do not fear - you can provide this flag to tell anvi'o to download the latest, freshest data directly "
                     "from KEGG's REST API and set it up into an anvi'o-compatible database."}
                ),
    'kegg-snapshot': (
            ['--kegg-snapshot'],
            {'default': None,
             'type': str,
             'metavar': 'RELEASE_NUM',
             'help': "If you are particularly interested in an earlier snapshot of KEGG that anvi'o knows about, you can set it here. "
                     "Otherwise anvi'o will always use the latest snapshot it knows about, which is likely to be the one associated with "
                     "the current release of anvi'o."}
                ),
    'hide-outlier-SNVs': (
            ['--hide-outlier-SNVs'],
            {'default': False,
             'action': 'store_true',
             'help': "During profiling, anvi'o marks positions of single-nucleotide variations (SNVs) "
                     "that originate from places in contigs where coverage values are a bit 'sketchy'. "
                     "If you would like to avoid SNVs in those positions of splits in applicable projects "
                     "you can use this flag, and the interface would hide SNVs that are marked as 'outlier' "
                     "(although it is clearly the best to see everything, no one will judge you if you end "
                     "up using this flag) (plus, there may or may not be some historical data on this here: "
                     "https://github.com/meren/anvio/issues/309)."}
                ),
    'hmmer-program': (
            ['--hmmer-program'],
            {'type': str,
            'required': False,
             'help': "Which of the HMMER programs to use to run HMMs (hmmscan or hmmsearch). By default "
                     "anvi'o will use hmmscan for typical HMM operations like those in anvi-run-hmms (as these "
                     "tend to scan a very large number of genes against a relatively small number of HMMs), "
                     "but if you are using this program to scan a very large number of HMMs, hmmsearch might "
                     "be a better choice for performance. For this reason, hmmsearch is the default in operations like "
                     "anvi-run-pfams and anvi-run-kegg-kofams. See this article for a discussion on the performance "
                     "of these two programs: https://cryptogenomicon.org/2011/05/27/hmmscan-vs-hmmsearch-speed-the-numerology/"}
                ),
    'hmm-source': (
            ['--hmm-source'],
            {'metavar': 'SOURCE NAME',
             'default': None,
             'help': "Use a specific HMM source. You can use '--list-hmm-sources' flag to see "
                     "a list of available resources. The default is '%(default)s'."}
                ),
    'hmm-sources': (
            ['--hmm-sources'],
            {'metavar': 'SOURCE NAME',
             'help': "Get sequences for a specific list of HMM sources. You can list one or more "
                     "sources by separating them from each other with a comma character (i.e., "
                     "'--hmm-sources source_1,source_2,source_3'). If you would like to see a list "
                     "of available sources in the contigs database, run this program with "
                     "'--list-hmm-sources' flag."}
                ),
    'list-hmm-sources': (
            ['-l', '--list-hmm-sources'],
            {'default': False,
             'action': 'store_true',
             'help': "List available HMM sources in the contigs database and quit."}
                ),
    'annotation-source': (
            ['--annotation-source'],
            {'metavar': 'SOURCE NAME',
             'default': None,
             'help': "Get functional annotations for a specific annotation source. You can use the flag "
                     "'--list-annotation-sources' to learn about what sources are available."}
                ),
    'annotation-sources': (
            ['--annotation-sources'],
            {'metavar': 'SOURCE NAME[S]',
             'default': None,
             'help': "Get functional annotations for a specific list of annotation sources. You "
                     "can specify one or more sources by separating them from each other with a comma "
                     "character (i.e., '--annotation-sources source_1,source_2,source_3'). The default "
                     "behavior is to return everything"}
                ),
    'list-annotation-sources': (
            ['-l', '--list-annotation-sources'],
            {'default': False,
             'action': 'store_true',
             'help': "List available functional annotation sources."}
                ),
    'aggregate-based-on-accession': (
            ['--aggregate-based-on-accession'],
            {'default': False,
             'action': 'store_true',
             'help': "This is important. When anvi'o aggregates functions for functional enrichment analyses "
                     "or to display them, it uses by default the 'function text' as keys. This is because "
                     "multiple accession IDs in various databases may correspond to the same function, and "
                     "when you are doing a functional enrichment analysis, you most likely would like to "
                     "avoid over-splitting of functions due to this. But then how can we know if you are "
                     "doing something that requires things to be aggregated based on accession ids for "
                     "functions rather than actual functions? We can't. But we have this flag here so you can "
                     "instruct anvi'o to listen to you and not to us."}
                ),
    'aggregate-using-all-hits': (
            ['--aggregate-using-all-hits'],
            {'default': False,
             'action': 'store_true',
             'help': "This program will aggregate functions based on best hits only, and this flag will change that "
                     "behavior. In some cases a gene may be annotated with multiple functions. This is a decision often "
                     "made at the level of function annotation tool. For instance, when you run `anvi-run-ncbi-cogs`, "
                     "you may end up having two COG annotations for a single gene because the gene hit both of them "
                     "with significance scores that were above the default noise cutoff. While this can be useful when "
                     "one visualizes functions or works with an `anvi-summarize` output where things should be most "
                     "comprehensive, having some genes annotated with multiple functions and others with one function "
                     "may over-split them (since in this scenario a gene with COGXXX and COGXXX;COGYYY would end up in "
                     "different bins). Thus, when working on functional enrichment analyses or displaying functions "
                     "anvi'o will only use the best hit for any gene that has multiple hits by default. But you can turn "
                     "that behavior off explicitly and show anvi'o who is the boss by using this flag."}
                ),

    'include-gc-identity-as-function': (
            ['--include-gc-identity-as-function'],
            {'default': False,
             'action': 'store_true',
             'help': "This is an option that asks anvi'o to treat gene cluster names as functions. By "
                     "doing so, you are in fact creating an opportunity to study functional enrichment "
                     "statistics for each gene cluster independently. For instance, multiple gene "
                     "clusters may have the same COG function. But if you wish to use the same enrichment "
                     "analysis in your pangenome without collapsing multiple gene clusters into a single "
                     "function name, you can use this flag, and ask for 'IDENTITY' as the functional "
                     "annotation source."}
                ),
    'gene-names': (
            ['--gene-names'],
            {'metavar': 'HMM HIT NAME',
             'help': "Get sequences only for a specific gene name. Each name should be separated from "
                     "each other by a comma character. For instance, if you want to get back only RecA "
                     "and Ribosomal_L27, you can type '--gene-names RecA,Ribosomal_L27', and you will "
                     "get any and every hit that matches these names in any source. If you would like "
                     "to see a list of available gene names, you can use '--list-available-gene-names' "
                     "flag."}
                ),
    'get-aa-sequences': (
            ['--get-aa-sequences'],
            {'default': False,
             'action': 'store_true',
             'help': "Store amino acid sequences instead."}
                ),
    'return-best-hit': (
            ['--return-best-hit'],
            {'default': False,
             'action': 'store_true',
             'help': "A bin may contain more than one hit for a gene name in a given HMM source. For instance, there may "
                     "be multiple RecA hits in a genome bin from Campbell et al.. Using this flag, will go through all of "
                     "the gene names that appear multiple times, and remove all but the one with the lowest e-value. Good "
                     "for whenever you really need to get only a single copy of single-copy core genes from a genome bin."}
                ),
    'max-num-genes-missing-from-bin': (
            ['--max-num-genes-missing-from-bin'],
            {'default': None,
             'metavar': 'INTEGER',
             'help': "This filter removes bins (or genomes) from your analysis. If you have a list of gene names, you can "
                     "use this parameter to omit any bin (or external genome) that is missing more than a number of genes "
                     "you desire. For instance, if you have 100 genome bins, and you are interested in working with 5 "
                     "ribosomal proteins, you can use '--max-num-genes-missing-from-bin 4' to remove the bins that "
                     "are missing more than 4 of those 5 genes. This is especially useful for phylogenomic analyses. "
                     "Parameter 0 will remove any bin that is missing any of the genes."}
                ),
    'min-num-bins-gene-occurs': (
            ['--min-num-bins-gene-occurs'],
            {'default': None,
             'metavar': 'INTEGER',
             'help': "This filter removes genes from your analysis. Let's assume you have 100 bins to get sequences for HMM "
                     "hits. If you want to work only with genes among all the hits that occur in at least X number of bins, "
                     "and discard the rest of them, you can use this flag. If you say '--min-num-bins-gene-occurs 90', each "
                     "gene in the analysis will be required at least to appear in 90 genomes. If a gene occurs in less than "
                     "that number of genomes, it simply will not be reported. This is especially useful for phylogenomic "
                     "analyses, where you may want to only focus on genes that are prevalent across the set of genomes "
                     "you wish to analyze."}
                ),
    'max-num-gene-clusters-missing-from-genome': (
            ['--max-num-gene-clusters-missing-from-genome'],
            {'default': 0,
             'metavar': 'INTEGER',
             'help': "This filter will remove genomes from your report. If you have a list of gene cluster names, you can "
                     "use this parameter to omit any genome from your report if it is missing more than a number of genes "
                     "you desire. For instance, if you have 100 genomes in your pan genome, and you are interested in "
                     "working only with genomes that have all 5 specific gene clusters of your choice, you can use "
                     "'--max-num-gene-clusters-missing-from-genome 4' to remove remove the bins that "
                     "are missing more than 4 of those 5 genes. This is especially useful for phylogenomic analyses. "
                     "Parameter 0 will remove any genome that is missing any of the genes."}
                ),
    'min-num-genomes-gene-cluster-occurs': (
            ['--min-num-genomes-gene-cluster-occurs'],
            {'default': 0,
             'metavar': 'INTEGER',
             'help': "This filter will remove gene clusters from your report. Let's assume you have 100 genomes in your pan "
                     "genome analysis. You can use this parameter if you want to work only with gene clusters that occur in "
                     "at least X number of genomes. If you say '--min-num-genomes-gene-cluster-occurs 90', each "
                     "gene cluster in the analysis will be required at least to appear in 90 genomes. If a gene occurs in "
                     "less than that number of genomes, it simply will not be reported. This is especially useful for "
                     "phylogenomic analyses, where you may want to only focus on gene clusters that are prevalent across "
                     "the set of genomes you wish to analyze."}
                ),
    'max-num-genomes-gene-cluster-occurs': (
            ['--max-num-genomes-gene-cluster-occurs'],
            {'default': sys.maxsize,
             'metavar': 'INTEGER',
             'help': "This filter will remove gene clusters from your report. Let's assume you have 100 genomes in your pan "
                     "genome analysis. You can use this parameter if you want to work only with gene clusters that occur in "
                     "at most X number of genomes. If you say '--max-num-genomes-gene-cluster-occurs 1', you will get gene "
                     "clusters that are singletons. Combining this parameter with --min-num-genomes-gene-cluster-occurs can "
                     "give you a very precise way to filter your gene clusters."}
                ),
    'min-num-genes-from-each-genome': (
            ['--min-num-genes-from-each-genome'],
            {'default': 0,
             'metavar': 'INTEGER',
             'help': "This filter will remove gene clusters from your report. If you say '--min-num-genes-from-each-genome 2', "
                     "this filter will remove every gene cluster, to which every genome in your analysis contributed less than "
                     "2 genes. This can be useful to find out gene clusters with many genes from many genomes (such as conserved "
                     "multi-copy genes within a clade)."}
                ),
    'max-num-genes-from-each-genome': (
            ['--max-num-genes-from-each-genome'],
            {'default': sys.maxsize,
             'metavar': 'INTEGER',
             'help': "This filter will remove gene clusters from your report. If you say '--max-num-genes-from-each-genome 1', "
                     "every gene cluster that has more than one gene from any genome that contributes to it will be removed "
                     "from your analysis. This could be useful to remove gene clusters with paralogs from your report for "
                     "appropriate phylogenomic analyses. For instance, using '--max-num-genes-from-each-genome 1' and "
                     "'min-num-genomes-gene-cluster-occurs X' where X is the total number of your genomes, would give you the "
                     "single-copy gene clusters in your pan genome."}
                ),
    'min-functional-homogeneity-index': (
            ['--min-functional-homogeneity-index'],
            {'default': -1,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This filter will remove gene clusters from your report. If you say '--min-functional-homogeneity-index 0.3', "
                     "every gene cluster with a functional homogeneity index less than 0.3 will be removed from your analysis. This "
                     "can be useful if you only want to look at gene clusters that are highly conserved in resulting function"}
                ),
    'max-functional-homogeneity-index': (
            ['--max-functional-homogeneity-index'],
            {'default': 1,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This filter will remove gene clusters from your report. If you say '--max-functional-homogeneity-index 0.5', "
                     "every gene cluster with a functional homogeneity index greater than 0.5 will be removed from your analysis. This "
                     "can be useful if you only want to look at gene clusters that don't seem to be functionally conserved"}
                ),
    'min-geometric-homogeneity-index': (
            ['--min-geometric-homogeneity-index'],
            {'default': -1,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This filter will remove gene clusters from your report. If you say '--min-geometric-homogeneity-index 0.3', "
                     "every gene cluster with a geometric homogeneity index less than 0.3 will be removed from your analysis. This "
                     "can be useful if you only want to look at gene clusters that are highly conserved in geometric configuration"}
                ),
    'max-geometric-homogeneity-index': (
            ['--max-geometric-homogeneity-index'],
            {'default': 1,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This filter will remove gene clusters from your report. If you say '--max-geometric-homogeneity-index 0.5', "
                     "every gene cluster with a geometric homogeneity index greater than 0.5 will be removed from your analysis. This "
                     "can be useful if you only want to look at gene clusters that have many not be as conserved as others"}
                ),
    'min-combined-homogeneity-index': (
            ['--min-combined-homogeneity-index'],
            {'default': -1,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This filter will remove gene clusters from your report. If you say '--min-combined-homogeneity-index 0.3', "
                     "every gene cluster with a combined homogeneity index less than 0.3 will be removed from your analysis. This "
                     "can be useful if you only want to look at gene clusters that are highly conserved overall"}
                ),
    'max-combined-homogeneity-index': (
            ['--max-combined-homogeneity-index'],
            {'default': 1,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This filter will remove gene clusters from your report. If you say '--max-combined-homogeneity-index 0.5', "
                     "every gene cluster with a combined homogeneity index greater than 0.5 will be removed from your analysis. This "
                     "can be useful if you only want to look at gene clusters that have many not be as conserved overall as others"}
                ),
    'add-into-items-additional-data-table': (
            ['--add-into-items-additional-data-table'],
            {'default': None,
             'metavar': 'NAME',
             'help': "If you use any of the filters, and would like to add the resulting item names into the items additional "
                     "data table of your database, you can use this parameter. You will need to give a name for these results to "
                     "be saved. If the given name is already in the items additional data table, its contents will be replaced "
                     "with the new one. Then you can run anvi-interactive or anvi-display-pan to 'see' the results of your filters."}
                ),
    'concatenate-genes': (
            ['--concatenate-genes'],
            {'default': False,
             'action': 'store_true',
             'help': "Concatenate output genes in the same order to create a multi-gene alignment output that is suitable "
                     "for phylogenomic analyses."}
                ),
    'separator': (
            ['--separator'],
            {'metavar': 'STRING',
             'default': None,
             'type': str,
             'help': "Characters to separate things (the default is whatever is most suitable)."}
                ),
    'align-with': (
            ['--align-with'],
            {'metavar': 'ALIGNER',
             'default': None,
             'type': str,
             'help': "The multiple sequence alignment program to use when multiple sequence alignment is necessary. To see "
                     "all available options, use the flag `--list-aligners`."}
                ),
    'list-aligners': (
            ['--list-aligners'],
            {'default': False,
             'action': 'store_true',
             'help': "Show available software for multiple sequence alignment."}
                ),
    'concatenate-gene-clusters': (
            ['--concatenate-gene-clusters'],
            {'default': False,
             'action': 'store_true',
             'help': "Concatenate output gene clusters in the same order to create a multi-gene alignment output that is suitable "
                     "for phylogenomic analyses."}
                ),
    'partition-file': (
            ['--partition-file'],
            {'metavar': 'FILE_PATH',
             'default': None,
             'type': str,
             'help': "Some commonly used software for phylogenetic analyses (e.g., IQ-TREE, RAxML, etc) allow users to "
             "specify/test different substitution models for each gene of a concatenated multiple sequence alignments. For "
             "this, they use a special file format called a 'partition file', which indicates the site for each gene in the "
             "alignment. You can use this parameter to declare an output path for anvi'o to report a NEXUS format partition "
             "file in addition to your FASTA output (requested by Massimiliano Molari in #1333)."}
                ),
    'report-DNA-sequences': (
            ['--report-DNA-sequences'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, this program reports amino acid sequences. Use this flag to report DNA sequences instead."}
                ),
    'skip-multiple-gene-calls': (
            ['--skip-multiple-gene-calls'],
            {'default': False,
             'action': 'store_true',
             'help': "When generating concatenated output skip gene clusters contain multiple gene calls."}
                ),
    'list-available-gene-names': (
            ['-L', '--list-available-gene-names'],
            {'default': False,
             'action': 'store_true',
             'help': "List available gene names in HMM sources selection and quit."}
                ),
    'search-terms': (
            ['--search-terms'],
            {'metavar': 'SEARCH_TERMS',
             'help': "Search terms. Multiple of them can be declared separated by a delimiter (the default is a comma)."}
                ),
    'sensitive': (
            ['--sensitive'],
            {'default': False,
             'action': 'store_true',
             'help': "DIAMOND sensitivity. With this flag you can instruct DIAMOND to be 'sensitive', rather than 'fast' "
                     "during the search. It is likely the search will take remarkably longer. But, hey, if you are doing "
                     "it for your final analysis, maybe it should take longer and be more accurate. This flag is only "
                     "relevant if you are running DIAMOND."}
                ),
    'gene-caller-ids': (
            ['--gene-caller-ids'],
            {'metavar': 'GENE_CALLER_IDS',
             'type': str,
             'help': "Gene caller ids. Multiple of them can be declared separated by a delimiter (the default is a comma). "
                     "In anvi-gen-variability-profile, if you declare nothing you will get all genes matching your other "
                     "filtering criteria. In other programs, you may get everything, nothing, or an error. It really depends "
                     "on the situation. Fortunately, mistakes are cheap, so it's worth a try."}
                ),
    'flank-mode': (
            ['--flank-mode'],
            {'action': 'store_true',
             'help': "If in --flank-mode, anvi-export-locus will extract a locus based on the coordinates "
                    "of flanking genes. You MUST provide 2 flanking genes in the form of TWO "
                    "--search-term, --gene-caller-ids, or --hmm-sources. The --flank-mode option is "
                    "appropriate for extracting loci of variable gene number lengths, but are consistently "
                    "located between the same flanking genes in the genome(s) of interest."}
              ),
    'num-genes': (
            ['-n','--num-genes'],
            {'metavar': 'NUM_GENES',
             'type': str,
             'help': "Required for DEFAULT mode. For each match (to the function, or HMM that was searched) a sequence which includes "
                     "a block of genes will be saved. The block could include either genes only in the forward direction of the gene (defined "
                     "according to the direction of transcription of the gene) or reverse or both. "
                     "If you wish to get both direction use a comma (no spaces) to define the block "
                     "For example, '-n 4,5' will give you four genes before and five genes after. "
                     "Whereas, '-n 5' will give you five genes after (in addition to the gene that matched). "
                     "To get only genes preceding the match use '-n 5,0'. If the number of genes requested "
                     "exceeds the length of the contig, then the output will include the sequence until the end "
                     "of the contig."}
              ),
    'gene-mode': (
            ['--gene-mode'],
            {'default': False,
             'action': 'store_true',
             'help': "Initiate the interactive interface in 'gene mode'. In this mode, the items are genes (instead of "
                     "splits of contigs). The following views are available: detection (the detection value of each gene "
                     "in each sample). The mean_coverage (the mean coverage of genes). The non_outlier_mean_coverage "
                     "(the mean coverage of the non-outlier nucleotide positions of each gene in each sample (median absolute "
                     "deviation is used to remove outliers per gene per sample)). The non_outlier_coverage_std view (standard deviation "
                     "of the coverage of non-outlier positions of genes in samples). You can also choose to order items "
                     "and layers according to each one of the aforementioned views. In addition, all layer ordering "
                     "that are available in the regular mode (i.e. the full mode where you have contigs/splits) are also "
                     "available in 'gene mode', so that, for example, you can choose to order the layers according to 'detection', and that "
                     "would be the order according to the detection values of splits, whereas if you choose 'genes_detections' "
                     "then the order of layers would be according to the detection values of genes. Inspection and sequence "
                     "functionality are available (through the right-click menu), except now sequences are of the specific gene. "
                     "Inspection has now two options available: 'Inspect Context', which brings you to the inspection page of the split "
                     "to which the gene belongs where the inspected gene will be highlighted in yellow in the bottom, and 'Inspect Gene', "
                     "which opens the inspection page only for the gene and 100 nts around each side of it (the purpose of this option "
                     "is to make the inspection page load faster if you only want to look at the nucleotide coverage of a specific gene). "
                     "NOTICE: You can't store states or collections in 'gene mode'. However, you still can make fake selections, and create "
                     "fake bins for your viewing convenience only (smiley). Search options are available, and you can even search for functions "
                     "if you have them in your contigs database. ANOTHER NOTICE: loading this mode might take a while if your bin "
                     "has many genes, and your profile database has many samples, this is because the gene coverages stats are "
                     "computed in an ad-hoc manner when you load this mode, we know this is not ideal and we plan to improve that "
                     "(along with other things). If you have suggestions/complaints regarding this mode please comment on this "
                     "github issue: https://goo.gl/yHhRei. Please refer to the online tutorial for more information."}
                ),
    'gene-caller-id': (
            ['--gene-caller-id'],
            {'metavar': 'GENE_CALLER_ID',
             'type': int,
             'help': "A single gene id."}
                ),
    'target-version': (
            ['-t', '--target-version'],
            {'metavar': 'VERSION',
             'type': int,
             'help': "Anvi'o will stop upgrading your database when it reaches to this version. "}
                ),
    'delimiter': (
            ['--delimiter'],
            {'metavar': 'CHAR',
             'default': ',',
             'help': "The delimiter to parse multiple input terms. The default is '%(default)s'."}
                ),
    'wrap': (
            ['--wrap'],
            {'metavar': 'WRAP',
             'default': 120,
             'type': int,
             'help': "When to wrap sequences when storing them in a FASTA file. The default is "
                     "'%(default)d'. A value of '0' would be equivalent to 'do not wrap'."}
                ),
    'no-wrap': (
            ['--no-wrap'],
            {'default': False,
             'action': 'store_true',
             'help': "Do not be wrap sequences nicely in the output file."}
                ),
    'leeway': (
            ['--leeway'],
            {'metavar': 'LEEWAY_NTs',
             'default': 100,
             'type': int,
             'help': "The minimum number of nucleotides for a given short read mapping into "
                     "the gene context for it to be reported. You must consider the length of "
                     "your short reads, as well as the length of the gene you are targeting. "
                     "The default is %(default)d nts."}
                ),
    'flank-length': (
            ['--flank-length'],
            {'metavar': 'INT',
             'default': 0,
             'type': int,
             'help': "Extend sequences for gene calls with additional nucleotides from both ends. If the seqeunce for "
                     "a target gene is between nucleotide positions START and STOP, using a flank lenght of M will give "
                     "you a sequence that starts at START - M and ends at STOP + M."}
              ),
    'split-R1-and-R2': (
            ['-Q', '--split-R1-and-R2'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, this program outputs 3 FASTA files for paired-end reads: one "
                     "for R1, one for R2, and one for unpaired reads."}
                ),
    'gzip-output': (
            ['-X', '--gzip-output'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, output file(s) will be gzip compressed and the extension `.gz` will be added."}
                ),
    'list-contigs': (
            ['--list-contigs'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, the program will list contigs in the BAM file and exit gracefully "
                     "without any further analysis."}
                ),
    'list-splits': (
            ['--list-splits'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, the program will list split names in the profile database and quite"}
                ),

    'list-collections': (
            ['--list-collections'],
            {'default': False,
             'action': 'store_true',
             'help': "Show available collections and exit."}
                ),
    'list-bins': (
            ['--list-bins'],
            {'default': False,
             'action': 'store_true',
             'help': "List available bins in a collection and exit."}
                ),
    'list-states': (
            ['--list-states'],
            {'default': False,
             'action': 'store_true',
             'help': "Show available states and exit."}
                ),
    'show-views': (
            ['--show-views'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, the program will show a list of available views, and exit."}
                ),
    'list-completeness-sources': (
            ['--list-completeness-sources'],
            {'default': False,
             'action': 'store_true',
             'help': "Show available sources and exit."}
                ),
    'completeness-source': (
            ['--completeness-source'],
            {'metavar': 'NAME',
             'help': "Single-copy gene source to use to estimate completeness."}
                ),
    'split-name': (
            ['--split-name'],
            {'metavar': 'SPLIT_NAME',
             'help': "Split name."}
                ),
    'contig-name': (
            ['--contig-name'],
            {'metavar': 'CONTIG_NAME',
             'help': "Contig name."}
                ),
    'program': (
            ['--program'],
            {'metavar': 'PROGRAM_NAME',
             'help': "Program name.",
             'required': False,
             'default': 'default'}
                ),
    'splits-of-interest': (
            ['--splits-of-interest'],
            {'metavar': 'FILE',
             'help': "A file with split names. There should be only one column in the file, and each line "
                     "should correspond to a unique split name."}
                ),
    'contigs-of-interest': (
            ['--contigs-of-interest'],
            {'metavar': 'FILE',
             'help': "It is possible to focus on only a set of contigs. If you would like to do that and ignore "
                     "the rest of the contigs in your contigs database, use this parameter with a flat file "
                     "every line of which desribes a single contig name."}
                ),
    'samples-of-interest': (
            ['--samples-of-interest'],
            {'metavar': 'FILE',
             'help': "A file with samples names. There should be only one column in the file, and each line "
                     "should correspond to a unique sample name (without a column header)."}
                ),
    'samples-txt': (
            ['--samples-txt'],
            {'metavar': 'FILE',
             'help': "A TAB-delimited file with columns ['sample', 'r1', 'r2'] or ['sample', 'group', 'r1', 'r2'] "
                     "where `r1` and `r2` columns are paths to compressed or flat FASTQ files for each `sample` and "
                     "`group` is an optional column for relevant applications where samples are affiliated with one-word "
                     "categorical variables that define to which group they are assigned."}
                ),
    'genes-of-interest': (
            ['--genes-of-interest'],
            {'metavar': 'FILE',
             'help': "A file with anvi'o gene caller IDs. There should be only one column in the file, and each line "
                     "should correspond to a unique gene caller id (without a column header)."}
                ),
    'gene-cluster-id': (
            ['--gene-cluster-id'],
            {'metavar': 'GENE_CLUSTER_ID',
             'help': "Gene cluster ID you are interested in."}
                ),
    'gene-cluster-ids-file': (
            ['--gene-cluster-ids-file'],
            {'metavar': 'FILE_PATH',
             'help': "Text file for gene clusters (each line should contain be a unique gene cluster id)."}
                ),
    'bin-id': (
            ['-b', '--bin-id'],
            {'metavar': 'BIN_NAME',
             'help': "Bin name you are interested in."}
                ),
    'bin-names-list': (
            ['-b', '--bin-names-list'],
            {'metavar': 'BIN NAMES',
             'help': "Comma-separated list of bin names."}
                ),
    'new-bin-name': (
            ['-B', '--new-bin-name'],
            {'metavar': 'BIN NAME',
             'help': "The new bin name."}
                ),
    'bin-ids-file': (
            ['-B', '--bin-ids-file'],
            {'metavar': 'FILE_PATH',
             'help': "Text file for bins (each line should be a unique bin id)."}
                ),
    'find-from-split-name': (
            ['--find-from-split-name'],
            {'metavar': 'SPLIT_NAME',
             'help': "If you don't know the bin name you want to work with but if you know the split name it contains "
                     "you can use this parameter to tell anvi'o the split name, and so it can find the bin for you "
                     "automatically. This is something extremely difficult for anvi'o to do, but it does it anyway "
                     "because you."}
                ),
    'collection-name': (
            ['-C', '--collection-name'],
            {'metavar': 'COLLECTION_NAME',
             'help': "Collection name."}
                ),
    'num-positions-from-each-split': (
            ['--num-positions-from-each-split'],
            {'metavar': 'INT',
             'default': 0,
             'type': int,
             'help': "Each split may have one or more variable positions. By default, anvi'o will report every SNV "
                     "position found in a given split. This parameter will help you to define a cutoff for the maximum "
                     "number of SNVs to be reported from a split (if the number of SNVs is more than the number you "
                     "declare using this parameter, the positions will be randomly subsampled)."}
             ),
    'min-scatter': (
            ['-m', '--min-scatter'],
            {'metavar': 'INT',
             'default': 0,
             'type': int,
             'help': "This one is tricky. If you have N samples in your dataset, a given variable position x in one "
                     "of your splits can split your N samples into `t` groups based on the identity of the "
                     "variation they harbor at position x. For instance, `t` would have been 1, if all samples had the same "
                     "type of variation at position x (which would not be very interesting, because in this case "
                     "position x would have zero contribution to a deeper understanding of how these samples differ "
                     "based on variability. When `t` > 1, it would mean that identities at position x across samples "
                     "do differ. But how much scattering occurs based on position x when t > 1? If t=2, how many "
                     "samples ended in each group? Obviously, even distribution of samples across groups may tell "
                     "us something different than uneven distribution of samples across groups. So, this parameter "
                     "filters out any x if 'the number of samples in the second largest group' (=scatter) is less "
                     "than -m. Here is an example: let's assume you have 7 samples. While 5 of those have AG, 2 "
                     "of them have TC at position x. This would mean scatter of x is 2. If you set -m to 2, this "
                     "position would not be reported in your output matrix. The default value for -m is "
                     "%(default)d, which means every `x` found in the database and survived previous filtering "
                     "criteria will be reported. Naturally, -m cannot be more than half of the number of samples. "
                     "Please refer to the user documentation if this is confusing."}
                ),
    'min-ratio-of-competings-nts': (
            ['-r', '--min-ratio-of-competings-nts'],
            {'metavar': 'RATIO',
             'default': 0,
             'type': float,
             'help': "Minimum ratio of the competing nucleotides at a given position. Default is %(default)d."}
                ),
    'max-num-unique-positions': (
            ['-n', '--max-num-unique-positions'],
            {'metavar': 'NUM_POSITIONS',
             'default': 0,
             'type': int,
             'help': "Maximum number of unique positions to be used in the network. This may be one way to avoid extremely "
                     "large network descriptions that would defeat the purpose of a quick visualization. If there are more "
                     "unique positions in the variability profile, the program will randomly select a subset of them to match "
                     "the `max-num-unique-positions`. The default is %(default)d, which means all positions should be reported. "
                     "Remember that the number of nodes in the network will also depend on the number of samples described in "
                     "the variability profile."}
                ),
    'num-threads': (
            ['-T', '--num-threads'],
            {'metavar': 'NUM_THREADS',
             'default': 1,
             'type': int,
             'help': "Maximum number of threads to use for multithreading whenever possible. Very conservatively, the default "
                     "is 1. It is a good idea to not exceed the number of CPUs / cores on your system. Plus, please "
                     "be careful with this option if you are running your commands on a SGE --if you are clusterizing your runs, "
                     "and asking for multiple threads to use, you may deplete your resources very fast."}
                ),
    'num-parallel-processes': (
            ['-P', '--num-parallel-processes'],
            {'metavar': 'NUM_PROCESSES',
             'default': 1,
             'type': int,
             'help': "Maximum number of processes to run in parallel. Please note that this is different than number of threads. If you "
                     "ask for 4 parallel processes, and 5 threads, anvi'o will run four processes in parallel and assign 5 threads "
                     "to each. For resource allocation you must multiply the number of processes and threads."}
                ),
    'variability-profile': (
            ['-V', '--variability-profile'],
            {'metavar': 'VARIABILITY_TABLE',
             'type': str,
             'required': False,
             'help': "The output of anvi-gen-variability-profile, or a different variant-calling output that has been converted to the "
                     "anvi'o format."}
                ),
    'min-coverage-in-each-sample': (
            ['--min-coverage-in-each-sample'],
            {'metavar': 'INT',
             'default': 0,
             'type': int,
             'help': "Minimum coverage of a given variable nucleotide position in all samples. If a nucleotide position "
                     "is covered less than this value even in one sample, it will be removed from the analysis. Default "
                     "is %(default)d."}
                ),
    'min-departure-from-reference': (
            ['-r', '--min-departure-from-reference'],
            {'metavar': 'FLOAT',
             'default': 0,
             'type': float,
             'help': "Takes a value between 0 and 1, where 1 is maximum divergence from the reference. Default is %(default)f. "
                     "The reference here observation that corresponds to a given position in the mapped context."}
                ),
    'max-departure-from-reference': (
            ['-z', '--max-departure-from-reference'],
            {'metavar': 'FLOAT',
             'default': 1,
             'type': float,
             'help': "Similar to '--min-departure-from-reference', but defines an upper limit for divergence. The "
                     "default is %(default)f."}
                ),
    'min-departure-from-consensus': (
            ['-j', '--min-departure-from-consensus'],
            {'metavar': 'FLOAT',
             'default': 0,
             'type': float,
             'help': "Takes a value between 0 and 1, where 1 is maximum divergence from the consensus for a given position. The "
                     "default is %(default)f. The consensus is the most frequent observation at a given position."}
                ),
    'max-departure-from-consensus': (
            ['-a', '--max-departure-from-consensus'],
            {'metavar': 'FLOAT',
             'default': 1,
             'type': float,
             'help': "Similar to '--min-departure-from-consensus', but defines an upper limit for divergence. The "
                     "default is %(default)f."}
                ),
    'min-occurrence-of-variable-positions': (
            ['-x', '--min-occurrence'],
            {'metavar': 'NUM_SAMPLES',
             'default': 1,
             'type': int,
             'help': "Minimum number of samples a nucleotide position should be reported as variable. Default is %(default)d. "
                     "If you set it to 2, for instance, each eligible variable position will be expected to appear in at least "
                     "two samples, which will reduce the impact of stochastic, or unintelligible variable positions."}
                ),
    'quince-mode': (
            ['--quince-mode'],
            {'default': False,
             'action': 'store_true',
             'help': "The default behavior is to report base frequencies of nucleotide positions only if there "
                     "is any variation reported during profiling (which by default uses some heuristics to minimize "
                     "the impact of error-driven variation). So, if there are 10 samples, and a given position has been "
                     "reported as a variable site during profiling in only one of those samples, there will be no "
                     "information will be stored in the database for the remaining 9. When this flag is "
                     "used, we go back to each sample, and report base frequencies for each sample at this position "
                     "even if they do not vary. It will take considerably longer to report when this flag is on, and the use "
                     "of it will increase the file size dramatically, however it is inevitable for some statistical approaches "
                     "(as well as for some beautiful visualizations)."}
                ),
    'include-contig-names': (
            ['--include-contig-names'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you would like contig names for each variable position to be included in the "
                     "output file as a column. By default, we do not include contig names since they can practically "
                     "double the output file size without any actual benefit in most cases."}
                ),
    'include-split-names': (
            ['--include-split-names'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you would like split names for each variable position to be included in the "
                     "output file as a column."}
                ),
    'include-additional-data': (
            ['--include-additional-data'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you would like to append data stored in the `amino_acid_additional_data` table as "
                     "additional columns to your output. NOTE: This is not yet implemented for the `nucleotide_additional_data` "
                     "table."}
                ),
    'include-site-pnps': (
            ['--include-site-pnps'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if you want per-site pN and pS added as additional columns. Synonymity "
                     "will be calculate with respect to the reference, with respect to the consenus, and with respect to the "
                     "most common consensus seen at that site across samples (popular consensus). This makes a total of 6 "
                     "added columns. This flag will be ignored if --engine is not CDN."}
                ),
    'engine': (
            ['--engine'],
            {'default': 'NT',
             'metavar': 'ENGINE',
             'type': str,
             'help': "Variability engine. The default is '%(default)s'."}
                ),
    'min-binding-frequency': (
            ['-m', '--min-binding-frequency'],
            {'metavar': 'FLOAT',
             'default': 0.2,
             'type': float,
             'help': "InteracDome has associated binding 'frequencies', which can be considered scores between 0 to 1 that "
                     "quantify how likely a position is to be involved in binding. Use this parameter to filter out low frequencies. "
                     "The default is %(default)f. Warning, your contigs database size will grow massively if this is set to 0.0, but "
                     "you're the boss."}
                ),
    'min-hit-fraction': (
            ['-f', '--min-hit-fraction'],
            {'metavar': 'FLOAT',
             'default': 0.5,
             'type': float,
             'help': "Any hits where the hit length--relative to the HMM profile--divided by the total HMM profile length, is less than this value, "
                     "it will be removed from the results and will not contribute to binding frequencies. The default is %(default)s"}
                ),
    'information-content-cutoff': (
            ['-t', '--information-content-cutoff'],
            {'metavar': 'FLOAT',
             'default': 4.0,
             'type': float,
             'help': "This parameter can be used to control for low-quality domain hits. Each domain is composed of positions (match states) "
                     "with varying degrees of conservancy, which can be quantified with information content (IC). High IC means highly conserved. "
                     "For example, IC = 4 corresponds to 95%% of the members of the Pfam sharing the same amino acid at that position. "
                     "By default, anvi'o demands that for an alignment of a user's gene with a Pfam HMM, the gene sequence must match with the "
                     "consensus amino acid of each match state that has IC > %(default)f. For context, it is common for a Pfam to not even have a "
                     "position with an IC > 4, so these represent truly very conserved positions. You can modify this with this parameter. For example, "
                     "if you think this is dumb, you can set this to 10000, and then no domain hits will be removed for this reason."}
                ),
    'driver': (
            ['--driver'],
            {'metavar': 'DRIVER',
             'type': str,
             'required': True,
             'help': "Automatic binning drivers. Available options '%(choices)s'."}
                ),
    'transpose': (
            ['--transpose'],
            {'default': False,
             'action': 'store_true',
             'help': "Transpose the input matrix file before clustering."}
                ),
    'skip-check-names': (
            ['--skip-check-names'],
            {'default': False,
             'action': 'store_true',
             'help': "For debugging purposes. You should never really need it."}
                ),
    'skip-news': (
            ['--skip-news'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't try to read news content from upstream."}
                ),
    'experimental-org-input-dir': (
            ['-i', '--input-directory'],
            {'metavar': 'DIR_PATH',
             'type': str,
             'help': "Input directory where the input files addressed from the configuration "
                     "file can be found (i.e., the profile database, if PROFILE.db::TABLE "
                     "notation is used in the configuration file)."}
                ),
    'clustering-name': (
            ['-N', '--name'],
            {'metavar': 'NAME',
             'type': str,
             'help': "The name to use when storing the resulting clustering in the database. "
                     "This name will appear in the interactive interface and other relevant "
                     "interfaces. Please consider using a short and descriptive single-word "
                     "(if you do not do that you will make anvi'o complain)."}
                ),
    'distance': (
            ['--distance'],
            {'metavar': 'DISTANCE_METRIC',
             'type': str,
             'default': constants.distance_metric_default,
             'help': "The distance metric for the hierarchical clustering. The default distance "
                     "metric is '%(default)s'. You can find the full list of distance metrics "
                     "either by making a mistake (such as entering a non-existent distance metric "
                     "and making anvi'o upset), or by taking a look at the help menu of the "
                     "hierarchy.distance.pdist function in the scipy.cluster module."}
                ),
    'linkage': (
            ['--linkage'],
            {'metavar': 'LINKAGE_METHOD',
             'type': str,
             'default': constants.linkage_method_default,
             'help': "The linkage method for the hierarchical clustering. The default linkage "
                     "method is '%(default)s', because that is the best one. It really is. We talked "
                     "to a lot of people and they were all like 'this is the best one available' and "
                     "it is just all out there. Honestly it is so good that we will build a wall around it "
                     "and make other linkage methods pay for it. But if you want to see a full "
                     "list of available ones you can check the hierarcy.linkage function in "
                     "the scipy.cluster module. Up to you really. But then you can't use %(default)s "
                     "anymore, and you would have to leave anvi'o right now."}
                ),
    'input-dir': (
            ['--input-dir'],
            {'metavar': 'DIR_PATH',
             'type': str,
             'help': "Directory path for input files"}
                ),
    'output-dir': (
            ['-o', '--output-dir'],
            {'metavar': 'DIR_PATH',
             'type': str,
             'help': "Directory path for output files"}
                ),
    'output-file': (
            ['-o', '--output-file'],
            {'metavar': 'FILE_PATH',
             'type': str,
             'help': "File path to store results."}
                ),
    'log-file': (
            ['--log-file'],
            {'metavar': 'FILE_PATH',
             'default': None,
             'type': str,
             'help': "File path to store debug/output messages."}
                ),
    'trna-hits-file': (
            ['--trna-hits-file'],
            {'metavar': 'FILE_PATH',
             'default': None,
             'type': str,
             'help': "File path to store raw hits from tRNA scan."}
                ),
    'trna-cutoff-score': (
            ['--trna-cutoff-score'],
            {'metavar': 'INT',
             'default': 20,
             'type': int,
             'help': "Minimum score to assume a hit comes from a proper tRNA gene (passed to the tRNAScan-SE). "
                     "The default is %(default)d. It can get any value between 0-100."}
                ),
    'also-scan-trnas': (
            ['--also-scan-trnas'],
            {'default': False,
             'action': 'store_true',
             'help': "Also scan tRNAs while you're at it."}
                ),
    'output-db-path': (
            ['-o', '--output-db-path'],
            {'metavar': 'DB_FILE_PATH',
             'type': str,
             'help': "Output file path for the new database."}
                ),
    'temporary-dir-path': (
            ['--temporary-dir-path'],
            {'metavar': 'PATH',
             'type': str,
             'help': "If you don't provide anything here, this program will come up with a temporary "
                     "directory path by itself to store intermediate files, and clean it later. If you "
                     "want to have full control over this, you can use this flag to define one."}
                ),
    'output-file-prefix': (
            ['-O', '--output-file-prefix'],
            {'metavar': 'FILENAME_PREFIX',
             'type': str,
             'help': "A prefix to be used while naming the output files (no file type "
                     "extensions please; just a prefix)."}
                ),
    'long-format': (
            ['--long-format'],
            {'default': False,
             'action': 'store_true',
             'help': "Report the output file as a long-format TAB-delmited file instead of a TAB-delimited "
                     "sparse matrix."}
                ),
    'matrix-format': (
            ['--matrix-format'],
            {'default': False,
             'action': 'store_true',
             'help': "Report the output as TAB-delmited sparse matrix files."}
                ),
    'raw-output': (
            ['--raw-output'],
            {'default': False,
             'action': 'store_true',
             'help': "Just store the raw output without any processing of the primary data structure."}
                ),
    'dry-run': (
            ['--dry-run'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't do anything real. Test everything, and stop right before wherever the developer "
                     "said 'well, this is enough testing', and decided to print out results."}
                ),
    'skip-dry-run': (
            ['--skip-dry-run'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't do a dry run. Just start the workflow! Useful when your job is so big it takes "
                     "hours to do a dry run."}
                ),
    'no-interactive': (
            ['--no-interactive'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't show anything interactive (if possible)."}
                ),

    'verbose': (
            ['--verbose'],
            {'default': False,
             'action': 'store_true',
             'help': "Be verbose, print more messages whenever possible."}
                ),
    'concise': (
            ['--concise'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't be verbose, print less messages whenever possible."}
                ),
    'just-do-it': (
            ['--just-do-it'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't bother me with questions or warnings, just do it."}
                ),
    'ip-address': (
            ['-I', '--ip-address'],
            {'metavar': 'IP_ADDR',
             'type': str,
             'default': '0.0.0.0',
             'help': "IP address for the HTTP server. The default ip address (%(default)s) should "
                     "work just fine for most."}
                ),
   'browser-path': (
            ['--browser-path'],
            {'metavar': 'PATH',
             'type': str,
             'default': None,
             'help': "By default, anvi'o will use your default browser to launch the interactive interface. If you "
                     "would like to use something else than your system default, you can provide a full path for an "
                     "alternative browser using this parameter, and hope for the best. For instance we are using "
                     "this parameter to call Google's experimental browser, Canary, which performs better with "
                     "demanding visualizations."}
                ),
   'api-url': (
            ['--api-url'],
            {'metavar': 'API_URL',
             'type': str,
             'default': 'https://anvi-server.org',
             'help': "Anvi'server url"}
                ),
    'port-number': (
            ['-P', '--port-number'],
            {'metavar': 'INT',
             'default': None,
             'type': int,
             'help': "Port number to use for anvi'o services. If nothing is declared, anvi'o will try to find "
                     "a suitable port number, starting from the default port number, %d." % constants.default_port_number}
                ),
    'user': (
            ['--user'],
            {'metavar': 'USERNAME',
             'default': None,
             'type': str,
             'help': "The user for an anvi'server."}
                ),
    'user-server-shutdown': (
            ['--user-server-shutdown'],
            {'default': False,
             'action': 'store_true',
             'help': "Allow users to shutdown an anvi'server via web interface."}
                ),
    'read-only': (
            ['--read-only'],
            {'default': False,
             'action': 'store_true',
             'help': "When the interactive interface is started with this flag, all 'database write' "
                     "operations will be disabled."}
                ),
    'server-only': (
            ['--server-only'],
            {'default': False,
             'action': 'store_true',
             'help': "The default behavior is to start the local server, and fire up a browser that "
                     "connects to the server. If you have other plans, and want to start the server "
                     "without calling the browser, this is the flag you need."}
                ),
    'password-protected': (
            ['--password-protected'],
            {'default': False,
             'action': 'store_true',
             'help': "If this flag is set, command line tool will ask you to enter a password and interactive "
                     "interface will be only accessible after entering same password. This option is recommended "
                     "for shared machines like clusters or shared networks where computers are not isolated."}
                ),
    'store-in-db': (
            ['--store-in-db'],
            {'default': False,
             'action': 'store_true',
             'help': "Store analysis results into the database directly."}
                ),
    'skip-store-in-db': (
            ['--skip-store-in-db'],
            {'default': False,
             'action': 'store_true',
             'help': "By default, analysis results are stored in the profile database. The use of "
                     "this flag will let you skip that"}
                ),
    'min-e-value': (
            ['-e', '--min-e-value'],
            {'metavar': 'E-VALUE',
             'default': 1e-15,
             'type': float,
             'help': "Minimum significance score of an HMM find to be considered as a valid hit. "
                     "Default is %(default)g."}
                ),
    'max-num-target-sequences': (
            ['--max-num-target-sequences'],
            {'metavar': 'NUMBER',
             'default': 20,
             'type': float,
             'help': "Maximum number of target sequences to request from BLAST or DIAMOND searches. The default is %(default)g%%."}
                ),
    'min-percent-identity': (
            ['--min-percent-identity'],
            {'metavar': 'PERCENT_IDENTITY',
             'default': 80.0,
             'type': float,
             'help': "Minimum percent identity. The default is %(default)g%%."}
                ),
    'min-full-percent-identity': (
            ['--min-full-percent-identity'],
            {'metavar': 'FULL_PERCENT_IDENTITY',
             'default': 20.0,
             'type': float,
             'help': "In some cases you may get high raw ANI estimates (percent identity scores) "
                     "between two genomes that have little to do with each other simply because only "
                     "a small fraction of their content may be aligned. This can be partly "
                     "alleviated by considering the *full* percent identity, which includes in its "
                     "calculation regions that did not align. For example, if the alignment is a "
                     "whopping 97 percent identity but only 8 percent of the genome aligned, the *full* "
                     "percent identity is 0.970 * 0.080 = 0.078 OR 7.8 percent. *full* percent "
                     "identity is always included in the report, but you can also use it as a filter "
                     "for other metrics, such as percent identity. This filter will set all ANI "
                     "measures between two genomes to 0 if the *full* percent identity is less than "
                     "you deem trustable. When you set a value, anvi'o will go through the ANI "
                     "results, and set all ANI measures between two genomes to 0 if the *full* "
                     "percent identity *between either of them* is less than the parameter described "
                     "here. The default is %(default)g."}
                ),
    'use-full-percent-identity': (
            ['--use-full-percent-identity'],
            {'action': 'store_true',
             'help': "Usually, percent identity is calculated only over aligned regions, and this "
                     "is what is used as a distance metric by default. But with this flag, "
                     "you can instead use the *full* percent identity as the distance metric. It is the "
                     "same as percent identity, except that regions that did not align are included "
                     "in the calculation. This means *full* percent identity will always be less than or "
                     "equal to percent identity. How is it calculated? Well if P is the percentage identity "
                     "calculated in aligned regions, L is the length of the genome, and A is the fraction "
                     "of the genome that aligned to a compared genome, the full percent identity is "
                     "P * (A/L). In other words, it is the percent identity multiplied by the alignment "
                     "coverage. For example, if the alignment is a whopping 97 percent identity but "
                     "only 8 percent of the genome aligned, the *full* percent identity is 0.970 * 0.080 "
                     "= 0.078, which is just 7.8 percent."}
                ),
    'min-alignment-fraction': (
            ['--min-alignment-fraction'],
            {'default': 0.0,
             'metavar': 'NUM',
             'type': float,
             'help': "In some cases you may get high raw ANI estimates "
                     "(percent identity scores) between two genomes that have little to do with each other "
                     "simply because only a small fraction of their content may be aligned. This filter will "
                     "set all ANI scores between two genomes to 0 if the alignment fraction is less than you "
                     "deem trustable. When you set a value, anvi'o will go through the ANI results, and set "
                     "percent identity scores between two genomes to 0 if the alignment fraction *between either "
                     "of them* is less than the parameter described here. The default is %(default)g."}
                ),
    'significant-alignment-length': (
            ['--significant-alignment-length'],
            {'default': None,
             'metavar': 'INT',
             'type': int,
             'help': "So --min-alignment-fraction "
                     "discards any hit that is coming from alignments that represent shorter fractions of genomes, "
                     "but what if you still don't want to miss an alignment that is longer than an X number of "
                     "nucleotides regardless of what fraction of the genome it represents? Well, this parameter is "
                     "to recover things that may be lost due to --min-alignment-fraction parameter. Let's say, "
                     "if you set --min-alignment-fraction to '0.05', and this parameter to '5000', anvi'o will keep "
                     "hits from alignments that are longer than 5000 nts, EVEN IF THEY REPRESENT less than 5 percent of "
                     "a given genome pair. Basically if --min-alignment-fraction is your shield to protect yourself "
                     "from incoming garbage, --significant-alignment-length is your chopstick to pick out those that "
                     "may be interesting, and you are a true warrior here."}
                ),
    'bins-info': (
            ['--bins-info'],
            {'metavar': 'BINS_INFO',
             'help': "Additional information for bins. The file must contain three TAB-delimited columns, "
                     "where the first one must be a unique bin name, the second should be a 'source', and the "
                     "last one should be a 7 character HTML color code (i.e., '#424242'). Source column must "
                     "contain information about the origin of the bin. If these bins are automatically "
                     "identified by a program like CONCOCT, this column could contain the program name and "
                     "version. The source information will be associated with the bin in various interfaces "
                     "so in a sense it is not *that* critical what it says there, but on the other hand it is, "
                     "becuse we should also think about people who may end up having to work with what we put "
                     "together later."}
                ),
    'bins': (
            ['--bins'],
            {'metavar': 'BINS_DATA',
             'help': "Tab-delimited file, first column contains tree leaves (gene clusters, splits, contigs etc.) "
                     "and second column contains which Bin they belong."}
      ),
    'contigs-mode': (
            ['--contigs-mode'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag if your binning was done on contigs instead of splits. Please refer "
                     "to the documentation for help."}
                ),
    'sample-name': (
            ['-S', '--sample-name'],
            {'metavar': 'NAME',
             'help': "It is important to set a sample name (using only ASCII letters and digits "
                     "and without spaces) that is unique (considering all others). If you do not "
                     "provide one, anvi'o will try to make up one for you based on other information "
                     "(although, you should never let the software decide these things)."}
                ),
    'project-name': (
            ['-n', '--project-name'],
            {'metavar': 'PROJECT_NAME',
             'help': "Name of the project. Please choose a short but descriptive name (so anvi'o can use "
                     "it whenever she needs to name an output file, or add a new table in a database, or name "
                     "her first born)."}
                ),
    'skip-hierarchical-clustering': (
            ['--skip-hierarchical-clustering'],
            {'default': False,
             'action': 'store_true',
             'help': "If you are not planning to use the interactive interface (or if you have other "
                     "means to add a tree of contigs in the database) you may skip the step where "
                     "hierarchical clustering of your items are preformed based on default clustering "
                     "recipes matching to your database type."}
                ),
    'skip-variability-tables': (
            ['--skip-variability-tables'],
            {'default': False,
             'action': 'store_true',
             'help': "Processing variability tables in profile database might take a very long time. With "
                     "this flag you will be asking anvi'o to skip them."}
                ),
    'enforce-hierarchical-clustering': (
            ['--enforce-hierarchical-clustering'],
            {'default': False,
             'action': 'store_true',
             'help': "If you have more than 25,000 splits in your merged profile, anvi-merge will automatically "
                     "skip the hierarchical clustering of splits (by setting --skip-hierarchical-clustering flag "
                     "on). This is due to the fact that computational time required for hierarchical clustering "
                     "increases exponentially with the number of items being clustered. Based on our experience "
                     "we decided that 25,000 splits is about the maximum we should try. However, this is not a "
                     "theoretical limit, and you can overwrite this heuristic by using this flag, which would "
                     "tell anvi'o to attempt to cluster splits regardless."}
                ),
    'compress-auxiliary-data': (
            ['--compress-auxiliary-data'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, the auxiliary data file in the resulting output will be compressed. This "
                     "saves space, but it takes long. Also, if you are planning to compress the entire "
                     "later using GZIP, it is even useless to do. But you are the boss!"}
                ),
    'cluster-contigs': (
            ['--cluster-contigs'],
            {'default': False,
             'action': 'store_true',
             'help': "Single profiles are rarely used for genome binning or visualization, and since "
                     "clustering step increases the profiling runtime for no good reason, the default "
                     "behavior is to not cluster contigs for individual runs. However, if you are "
                     "planning to do binning on one sample, you must use this flag to tell anvi'o to "
                     "run cluster configurations for single runs on your sample."}
                ),
    'num-clusters-requested': (
            ['--num-clusters-requested'],
            {'metavar': 'INT',
             'default': 400,
             'type': int,
             'help': "How many clusters do you request? Default is %(default)d."}
             ),
    'overwrite-output-destinations': (
            ['-W', '--overwrite-output-destinations'],
            {'default': False,
             'action': 'store_true',
             'help': "Overwrite if the output files and/or directories exist."}
                ),
    'delete-if-exists': (
            ['--delete-if-exists'],
            {'default': False,
             'action': 'store_true',
             'help': "Be bold (at your own risk), and delete if exists."}
                ),
    'report-variability-full': (
            ['--report-variability-full'],
            {'default': False,
             'action': 'store_true',
             'help': "One of the things anvi-profile does is to store information about variable "
                     "nucleotide positions (SNVs). Usually it does not report every variable position, since "
                     "not every variable position is genuine variation. Say, if you have 1,000 coverage, "
                     "and all nucleotides at that position are Ts and only one of them is a C, the "
                     "confidence of that C being a real variation is quite low. anvi'o has a simple "
                     "algorithm in place to reduce the impact of noise. However, using this flag "
                     "you can disable it and ask profiler to report every single variation (which "
                     "may result in very large output files and millions of reports, but you are the "
                     "boss). Do not forget to take a look at '--min-coverage-for-variability' parameter. "
                     "Also note that this flag controls indel reporting: normally '--min-coverage-for-variability' "
                     "and internal anvi'o heuristics control whether or not indels should be reported, but with this "
                     "flag all indels are reported."}
                ),
    'report-extended-deflines': (
            ['--report-extended-deflines'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, the deflines in the resulting FASTA file will contain more information."}
                ),
    'manual-mode': (
            ['--manual-mode'],
            {'default': False,
             'action': 'store_true',
             'help': "Using this flag, you can run the interactive interface in an ad hoc manner using "
                     "input files you curated instead of standard output files generated by an anvi'o "
                     "run. In the manual mode you will be asked to provide a profile database. In this "
                     "mode a profile database is only used to store 'state' of the interactive interface "
                     "so you can reload your visual settings when you re-analyze the same files again. If "
                     "the profile database you provide does not exist, anvi'o will create an empty one for "
                     "you."}
                ),
    'hmm-profile-dir': (
            ['-H', '--hmm-profile-dir'],
            {'metavar': 'HMM PROFILE PATH',
             'help': "You can use this parameter you can specify a directory path that contain an HMM profile. "
                     "This way you can run HMM profiles that are not included in anvi'o. See the online "
                     "to find out about the specifics of this directory structure ."}
                ),
    'domtblout': (
            ['-F', '--domtblout'],
            {'metavar': 'HMM OUTPUT FORMAT',
             'type': str,
             'help': "This flag will provide the domain hits table (protein search only) from hmmsearch to a specified path."
                     "The output file will contain the suffix '_domtable.txt'."}
                ),
    'installed-hmm-profile': (
            ['-I', '--installed-hmm-profile'],
            {'metavar': 'HMM PROFILE NAME(S)'}
                ),
    'hmmer-output-dir': (
            ['--hmmer-output-dir'],
            {'metavar': 'OUTPUT DIRECTORY PATH',
             'help': "If you provide a path with this parameter, then the HMMER output file(s) will be saved "
                     "in this directory. Please note that this will only work if you are running on only one "
                     "profile using the -I flag."}
                ),
    'get-domtable-output': (
            ['--get-domtable-output'],
            {'default': False,
             'type': str,
             'help': "Use this flag in conjunction with --hmmer-output-dir to request domain table output "
                     "from HMMER (i.e., the file specified by the --domtblout flag from hmmsearch or hmmscan). Otherwise, only the regular "
                     "--tblout file will be stored in the specified directory. Please note that even if you use "
                     "this flag, the HMM hits stored in the database will be taken from the --tblout file only. "
                     "Also, this option only works with HMM profiles for amino acid sequences (not nucleotides)."}
                ),
    'min-contig-length': (
            ['-M', '--min-contig-length'],
            {'metavar': 'INT',
             'default': 1000,
             'type': int,
             'help': "Minimum length of contigs in a BAM file to analyze. The minimum length should be long enough "
                     "for tetra-nucleotide frequency analysis to be meaningful. There is no way to define a golden "
                     "number of minimum length that would be applicable to genomes found in all environments, but we "
                     "chose the default to be %(default)d, and have been happy with it. You are welcome to experiment, "
                     "but we advise to never go below 1,000. You also should remember that the lower you go, the more "
                     "time it will take to analyze all contigs. You can use --list-contigs parameter to have an idea how "
                     "many contigs would be discarded for a given M."}
                ),
    'max-contig-length': (
            ['--max-contig-length'],
            {'metavar': 'INT',
             'default': 0,
             'type': int,
             'help': "Just like the minimum contig length parameter, but to set a maximum. Basically this will remove "
                     "any contig longer than a certain value. Why would anyone need this? Who knows. But if you ever "
                     "do, it is here."}
                ),
    'min-mean-coverage': (
            ['-X', '--min-mean-coverage'],
            {'metavar': 'INT',
             'default': 0,
             'type': int,
             'help': "Minimum mean coverage for contigs to be kept in the analysis. The default value is %(default)d, "
                     "which is for your best interest if you are going to profile multiple BAM files which are then "
                     "going to be merged for a cross-sectional or time series analysis. Do not change it if you are not "
                     "sure this is what you want to do."}
                ),
    'min-coverage-for-variability': (
            ['-V', '--min-coverage-for-variability'],
            {'metavar': 'INT',
             'default': 10,
             'type': int,
             'help': "Minimum coverage of a nucleotide position to be subjected to SNV profiling. By default, anvi'o will "
                     "not attempt to make sense of variation in a given nucleotide position if it is covered less than "
                     "%(default)dX. You can change that minimum using this parameter. This parameter also controls the minimum "
                     "coverage for reporting indels. If an indel is observed at a position, yet the coverage of the position "
                     "in the contig where the indel starts is less than this parameter, the indel will be discarded."}
                ),
    'contigs-and-positions': (
            ['--contigs-and-positions'],
            {'metavar': 'CONTIGS_AND_POS',
             'required': True,
             'help': "This is the file where you list the contigs, and nucleotide positions you are interested in. This "
                     "is supposed to be a TAB-delimited file with two columns. In each line, the first column should be "
                     "the contig name, and the second column should be the comma-separated list of integers for nucleotide "
                     "positions."}
                ),
    'state-autoload': (
            ['--state-autoload'],
            {'metavar': 'NAME',
             'help': "Automatically load previous saved state and draw tree. To see a list of available states, "
                     "use --show-states flag."}
                ),
    'load-full-state': (
            ['--load-full-state'],
            {'required': False,
             'action': 'store_true',
             'help': "Often the minimum and maximum values defined for the an entire profile database that contains "
                     "all contigs do not scale well when you wish to work with a single bin in the refine mode. For "
                     "this reason, the default behavior of anvi-refine is to ignore min/max values set in the default "
                     "state. This flag is your way of telling anvi'o to not do that, and load the state stored in the "
                     "profile database as is. Please note that this variable has no influence on the `detection` view. "
                     "For the `detection` view, anvi'o will always load the global detection settings as if you have "
                     "used this flag."}
                ),
    'state': (
            ['-s', '--state'],
            {'metavar': 'STATE',
             'help': "State file, you can export states from database using anvi-export-state program"}
                ),
    'collection-autoload': (
            ['--collection-autoload'],
            {'metavar': 'NAME',
             'help': "Automatically load a collection and draw tree. To see a list of available collections, "
                     "use --list-collections flag."}
                ),
    'full-report': (
            ['--full-report'],
            {'metavar': 'FILE_NAME',
             'default': None,
             'help': "Optional output file with a fuller description of findings."}
                ),
    'include-sequences': (
            ['--include-sequences'],
            {'default': False,
             'action': 'store_true',
             'help': "Include sequences in the report."}
                ),
    'show-states': (
            ['--show-states'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared the program will print all available states and exit."}
                ),
    'skip-init-functions': (
            ['--skip-init-functions'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, function calls for genes will not be initialized (therefore will be missing from all "
                     "relevant interfaces or output files). The use of this flag may reduce the memory fingerprint and "
                     "processing time for large datasets."}
                ),
    'init-gene-coverages': (
            ['--init-gene-coverages'],
            {'default': False,
             'action': 'store_true',
             'help': "Initialize gene coverage and detection data. This is a very computationally expensive step, but it is "
                     "necessary when you need gene level coverage data. The reason this is very computationally expensive "
                     "is because anvi'o computes gene coverages by going back to actual coverage values of each gene to "
                     "average them, instead of using contig average coverage values, for extreme accuracy."}
                ),
    'reformat-contig-names': (
            ['--reformat-contig-names'],
            {'default': False,
             'action': 'store_true',
             'help': "Reformat contig names while generating the summary output so they look fancy. With this flag, anvi'o "
                     "will replace the original names of contigs to those that include the bin name as a prefix in resulting "
                     "summary output files per bin. Use this flag carefully as it may influence your downstream analyses due "
                     "to the fact that your original contig names in your input FASTA file for the contigs database will not "
                     "be in the summary output. Although, anvi'o will report a conversion map per bin so you can recover the "
                     "original contig name if you have to."}
                ),
    'skip-auto-ordering': (
            ['--skip-auto-ordering'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, the attempt to include automatically generated orders of items based on additional data "
                     "is skipped. In case those buggers cause issues with your data, and you still want to see your stuff and "
                     "deal with the other issue maybe later."}
                ),
    'quick-summary': (
            ['--quick-summary'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared the summary output will be generated as quickly as possible, with minimum amount "
                     "of essential information about bins."}
                ),
    'only-complete-links': (
            ['--only-complete-links'],
            {'default': False,
             'action': 'store_true',
             'help': "When declared, only reads that cover all positions will be reported. It is necessary to use this "
                     "flag if you want to perform oligotyping-like analyses on matching reads."}
                ),
    'add-coverage': (
            ['--add-coverage'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag to request that coverage and detection values be added as columns in long-format "
                     "output files. You must provide the profile database corresonding to your contigs db for this to work."}
                ),
    'users-data-dir': (
            ['-U', '--users-data-dir'],
            {'metavar': 'USERS_DATA_DIR',
             'type': str,
             'help': "Input directory where the user database is read and stored by the server. A new database will be "
                     "created if no directory is found."}
                ),
    'smtp-config-file': (
            ['-E', '--smtp-config-file'],
            {'metavar': 'SMTP_CONFIG_INI',
             'type': str,
             'help': "The configuration file for SMTP server to send e-mails. The input file should be formatted as an INI "
                     "file that starts with the header '[SMTP]', and should describe values of each of these variables in "
                     "the following lines: 'from_address' (the e-mail address that should appear in the 'From' section of "
                     "e-mails sent by the server), 'server_address' (the address of the SMTP server to connect), 'server_port' "
                     "(the port number to connect), 'init_tls' (whether to initialize TLS protocol), 'username' (the username "
                     "for the server to login, if necessary), 'password' (the password associated with the username for login, "
                     "if the password is not blank)."}
                ),
    'validate-users-automatically': (
            ['--validate-users-automatically'],
            {'default': True,
             'action': 'store_true',
             'help': "If this is true, users will not receive a link via email to confirm their account but instead be validated "
                     "automatically if there is no smtp configuration."}
                ),
    'queue-size': (
            ['--queue-size'],
            {'default': 0,
             'metavar': 'INT',
             'required': False,
             'help': "The queue size for worker threads to store data to communicate to the main thread. The default is set by the "
                     "class based on the number of threads. If you have *any* hesitation about whether you know what you are doing, "
                     "you should not change this value."}
                ),
    'ngram-window-range': (
            ['--ngram-window-range'],
            {'default': "2:3",
             'metavar': "NGRAM_WINDOW_RANGE",
             'type': str,
             'required': False,
             'help': "The range of window sizes of Ngrams to analyze for synteny patterns."
                     "Please format the window-range as x:y (e.g. Window sizes 2 to 4 would be denoted as: 2:4)"}
                ),
    'write-buffer-size': (
            ['--write-buffer-size'],
            {'default': 500,
             'metavar': 'INT',
             'required': False,
             'help': "How many items should be kept in memory before they are written to the disk. The default is "
                     "%(default)d. The larger the buffer size, the less frequently the program will access the disk, yet the more memory "
                     "will be consumed since the processed items will be cleared off the memory only after they are written "
                     "to the disk. The default buffer size will likely work for most cases, but if "
                     "you feel you need to reduce it, we trust you. Please keep an eye on the memory "
                     "usage output to make sure the memory use never exceeds the size of the "
                     "physical memory."}
                ),
    'write-buffer-size-per-thread': (
            ['--write-buffer-size-per-thread'],
            {'default': 500,
             'metavar': 'INT',
             'required': False,
             'help': "How many items should be kept in memory before they are written do the disk. The default is "
                     "%(default)d per thread. So a single-threaded job would have a write buffer size of "
                     "%(default)d, whereas a job with 4 threads would have a write buffer size of 4*%(default)d. "
                     "The larger the buffer size, the less frequent the program will access to the disk, yet the more memory "
                     "will be consumed since the processed items will be cleared off the memory only after they are written "
                     "to the disk. The default buffer size will likely work for most cases. Please keep an eye on the memory "
                     "usage output to make sure the memory use never exceeds the size of the physical memory."}
                ),
    'export-gff3': (
        ['--export-gff3'],
        {
            'default': False,
            'action': 'store_true',
            'help': "If this is true, the output file will be in GFF3 format."
        }
    ),
    'export-svg': (
            ['--export-svg'],
            {'type': str,
             'metavar': 'FILE_PATH',
             'required': False,
             'help': "The SVG output file path."}
                ),
    'tab-delimited': (
            ['--tab-delimited'],
            {'default': False,
             'required': False,
             'action': 'store_true',
             'help': "Use the TAB-delimited format for the output file."}
                ),
    'splits-mode': (
            ['--splits-mode'],
            {'default': False,
             'action': 'store_true',
             'help': "Specify this flag if you would like to output coverages of individual 'splits', rather than their 'parent' "
                     "contig coverages."}
                ),
    'report-as-text': (
            ['--report-as-text'],
            {'default': False,
             'action': 'store_true',
             'help': "If you give this flag, Anvi'o will not open new browser to show Contigs database statistics and write all stats "
                     "to TAB separated file and you should also give --output-file with this flag otherwise Anvi'o will complain."}
                ),
    'dump-dir': (
            ['--dump-dir'],
            {'required': False,
             'help': "Modeling and annotating structures requires a lot of moving parts, each which have "
                     "their own outputs. The output of this program is a structure database containing the "
                     "pertinent results of this computation, however a lot of stuff doesn't make the cut. "
                     "By providing a directory for this parameter you will get, in addition to the structure "
                     "database, a directory containing the raw output for everything."}
                ),
    'include-subdirs': (
            ['--include-subdirs'],
            {'default': False,
             'action': 'store_true',
             'help': "Also search subdirectories for files."}
                ),
    'workflow': (
            ['-w', '--workflow'],
            {'required': False,
             'help': "You must specify a workflow name. To see a list of available workflows "
                     "run --list-workflows."}
                ),
    'list-workflows': (
            ['--list-workflows'],
            {'required': False,
             'action': 'store_true',
             'help': "Print a list of available snakemake workflows"}
                ),
    'save-workflow-graph': (
            ['--save-workflow-graph'],
            {'required': False,
             'action': 'store_true',
             'help': "Save a graph representation of the workflow. If you are using this flag and if your "
                     "system is unable to generate such graph outputs, you will hear anvi'o complaining "
                     "(still, totally worth trying)."}
                ),
    'get-default-config': (
            ['--get-default-config'],
            {'metavar': 'OUTPUT_FILENAME',
             'type': str,
             'help': "Store a json formatted config file with all the default settings of the "
                     "workflow. This is a good draft you could use in order to write your own "
                     "config file. This config file contains all parameters that could be configured "
                     "for this workflow. NOTICE: the config file is provided with default values "
                     "only for parameters that are set by us in the workflow. The values for the rest "
                     "of the parameters are determined by the relevant program."}
                ),
    'list-dependencies': (
            ['--list-dependencies'],
            {'required': False,
             'action': 'store_true',
             'help': "Print a list of the dependencies of this workflow. You must provide a workflow name "
                     "and a config file. snakemake will figure out which rules need to be run according "
                     "to your config file, and according to the files available on your disk. According "
                     "to the rules that need to be run, we will let you know which programs are going to "
                     "be used, so that you can make sure you have all of them installed and loaded."}
                ),
    'config-file': (
            ['-c', '--config-file'],
            {'required': False,
             'help': "A JSON-formatted configuration file."}
                ),
    'additional-params': (
            ['-A', '--additional-params'],
            {'required': False,
             'nargs':'...', 'type':str,
             'help': "Additional snakemake parameters to add when running snakemake. NOTICE: --additional-params "
                     "HAS TO BE THE LAST ARGUMENT THAT IS PASSED TO anvi-run-workflow, ANYTHING THAT "
                     "FOLLOWS WILL BE CONSIDERED AS PART OF THE ADDITIONAL PARAMETERS THAT ARE PASSED TO SNAKEMAKE. "
                     "Any parameter that is accepted by snakemake should be fair game here, but it is your "
                     "responsibility to make sure that whatever you added makes sense. To see what parameters are "
                     "available please refer to the snakemake documentation. For example, you could use this to set "
                     "up cluster submission using --additional-params --cluster 'YOUR-CLUSTER-SUBMISSION-CMD'."}
                ),
    'self-key': (
            ['--self-key'],
            {'default': None,
             'type': str,
             'help': "The key you wish to set or change."}
                ),
    'self-value': (
            ['--self-value'],
            {'default': None,
             'type': str,
             'help': "The value you wish to set for the self key."}
                ),
    'no-variability': (
            ['--no-variability'],
            {'required': False,
             'action': 'store_true',
             'help': "If provided, no measures of sequence heterogeneity (from short read data) will be overlaid "
                     "on structures."}
                ),
    'compute-gene-coverage-stats': (
            ['--compute-gene-coverage-stats'],
            {'required': False,
             'action': 'store_true',
             'help': "If provided, gene coverage statistics will be appended for each entry in variability report. "
                     "This is very useful information, but will not be included by default because it is an expensive "
                     "operation, and may take some additional time."}
                ),
    'repository': (
            ['--repository'],
            {'default': 'merenlab/anvio',
             'type': str,
             'help': "Source repository to download releases, currently only Github is supported. Enter in 'merenlab/anvio' format."}
                ),
    'inseq-stats': (
            ['--inseq-stats'],
            {'required': False,
             'action': 'store_true',
             'default': False,
             'help': "Provide if working with INSeq/Tn-Seq genomic data. With this, all gene level "
                     "coverage stats will be calculated using INSeq/Tn-Seq statistical methods."}
                ),
    'migrate-dbs-safely': (
            ['--migrate-dbs-safely'],
            {'required': False,
             'action': 'store_true',
             'default': False,
             'help': "If you chose this, anvi'o will first create a copy of your original database. If something "
                     "goes wrong, it will restore the original. If everything works, it will remove the old copy. "
                     "IF YOU HAVE DATABASES THAT ARE VERY LARGE OR IF YOU ARE MIGRATING MANY MANY OF THEM THIS "
                     "OPTION WILL ADD A HUGE I/O BURDEN ON YOUR SYSTEM. But still. Safety is safe."}
                ),
    'migrate-dbs-quickly': (
            ['--migrate-dbs-quickly'],
            {'required': False,
             'action': 'store_true',
             'default': False,
             'help': "If you chose this, anvi'o will migrate your databases in place. It will be much faster (and arguably "
                     "more fun) than the safe option, but if something goes wrong, you will lose data. During the first "
                     "five years of anvi'o development not a single user lost data using our migration scripts as far as "
                     "we know. But there is always a first, and today might be your lucky day."}
                ),
    'module-completion-threshold': (
            ['--module-completion-threshold'],
            {'default': 0.75,
             'metavar': 'NUM',
             'type': float,
             'help': "This threshold defines the point at which we consider a KEGG module to be 'complete' or "
                     "'present' in a given genome or bin. It is the fraction of steps that must be complete in "
                     " in order for the entire module to be marked complete. The default is %(default)g."}
                ),
    'get-raw-data-as-json': (
            ['--get-raw-data-as-json'],
            {'default': None,
            'metavar': 'FILENAME_PREFIX',
            'type': str,
            'help': "If you want the raw metabolism estimation data dictionary in JSON-format, provide a filename prefix to this argument."
                    "The program will then output a file with the .json extension containing this data."}
                ),
    'store-json-without-estimation': (
            ['--store-json-without-estimation'],
            {'default': False,
             'action': 'store_true',
             'help': "This flag is used to control what is stored in the JSON-formatted metabolism data dictionary. When this flag is provided alongside the "
                    "--get-raw-data-as-json flag, the JSON file will be created without running metabolism estimation, and "
                    "that file will consequently include only information about KOfam hits and gene calls. The idea is that you can "
                    "then modify this file as you like and re-run this program using the flag --estimate-from-json."}
                ),
    'estimate-from-json': (
            ['--estimate-from-json'],
            {'default': None,
             'metavar': 'FILE_PATH',
             'type': str,
             'help': "If you have a JSON file containing KOfam hits and gene call information from your contigs database "
                     "(such as a file produced using the --get-raw-data-as-json flag), you can provide that file to this flag "
                     "and KEGG metabolism estimates will be computed from the information within instead of from a contigs database."}
                ),
    'kegg-output-modes': (
            ['--kegg-output-modes'],
            {'default': None,
             'metavar': 'MODES',
             'type': str,
             'help': "Use this flag to indicate what information you want in the kegg metabolism output files, by "
                     "providing a comma-separated list of output modes (each 'mode' you provide will result in a "
                     "different output file, all with the same prefix). The default output modes are 'kofam_hits' and "
                     "'complete_modules'. To see a list of available output modes, run this script with the flag "
                     "--list-available-modes."}
                ),
    'list-available-modes': (
            ['--list-available-modes'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag to see the available output modes and their descriptions."}
                ),
    'custom-output-headers': (
            ['--custom-output-headers'],
            {'default': None,
             'metavar': 'HEADERS',
             'type': str,
             'help': "For use with the 'custom' output mode. Provide a comma-separated list of headers to include "
                     "in the output matrix. To see a list of available headers, run this script with the flag "
                     "--list-available-output-headers."}
                ),
    'list-available-output-headers': (
            ['--list-available-output-headers'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag to see the available output headers."}
                ),
    'keep-all-hits': (
            ['--keep-all-hits'],
            {'default': False,
             'action': 'store_true',
             'help': "If you use this flag, anvi'o will not get rid of any raw HMM hits, even those that "
                     "are below the score threshold."}
                ),
    'log-bitscores': (
            ['--log-bitscores'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag to generate a tab-delimited text file containing the bit scores "
                     "of every KOfam hit that is put in the contigs database."}
                ),
    'heuristic-e-value': (
            ['-E', '--heuristic-e-value'],
            {'default': 1.0e-5,
             'metavar': 'FLOAT',
             'type': float,
             'help': "When considering hits that didn't quite make the bitscore cut-off for a gene, we "
                     "will only look at hits with e-values <= this number. (This is X.)"}
                ),
    'heuristic-bitscore-fraction': (
            ['-H', '--heuristic-bitscore-fraction'],
            {'default': 0.75,
             'metavar': 'FLOAT',
             'type': float,
             'help': "When considering hits that didn't quite make the bitscore cut-off for a gene, we "
                     "will only look at hits with bitscores > the KEGG threshold * this number. (This is Y.) "
                     "It should be a fraction between 0 and 1 (inclusive)."}
                ),
    'skip-bitscore-heuristic':(
            ['--skip-bitscore-heuristic'],
            {'default': False,
             'action': 'store_true',
             'help': "If you just want annotations from KOfam hits that are above the KEGG bitscore "
                     "threshold, use this flag to skip the mumbo-jumbo we do here to relax those thresholds. "}
                ),
    'include-metadata': (
            ['--include-metadata'],
            {'default': False,
            'action': 'store_true',
            'help': "When asking for --matrix-format, you can use this flag to make sure the output matrix files include "
                    "columns with metadata for each KEGG Module or KO (like the module name and category for example) before "
                    "the sample columns."}
                ),
    'only-complete': (
            ['--only-complete'],
            {'default': False,
            'action': 'store_true',
            'help': "Choose this flag if you want only modules over the module completeness threshold to be included "
                    "in any output files."}
                ),
    'include-zeros': (
            ['--include-zeros'],
            {'default': False,
            'action': 'store_true',
            'help': "If you use this flag, output files will include modules with 0 percent completeness score, "
                    "and in the case of --matrix-format, output matrices will include rows with 0s in every sample. "}
                ),
    'module-specific-matrices': (
            ['--module-specific-matrices'],
            {'default': None,
            'metavar': 'MODULE_LIST',
            'help': "Provide a comma-separated list of module numbers to this parameter, and then you will get "
                    "a KO hits matrix for each module in the list."}

                ),
    'no-comments': (
            ['--no-comments'],
            {'default': False,
            'action': 'store_true',
            'help': "If you are requesting --module-specific-matrices but you don't want those matrices to include "
                    "comment lines in them (for example, perhaps you want to use them for clustering), you can use "
                    "this flag. Otherwise, by default these specific matrices will include comments delineating "
                    "which KOs are in each step of the module."}
                ),
    'modules-txt': (
            ['-M', '--modules-txt'],
            {'default': None,
            'metavar': 'TEXT_FILE',
            'help': "A tab-delimited text file specifying module completeness in every genome/MAG/sample "
                    "that you are interested in. The best way to get this file is to run `anvi-estimate-metabolism "
                    "--kegg-output-modes modules` on your samples of interest. Trust us."}
                ),
    'groups-txt': (
            ['-G', '--groups-txt'],
            {'default': None,
            'metavar': 'TEXT_FILE',
            'help': "A tab-delimited text file specifying which group each item belongs to. "
                    "Depending on the context, items here may be individual samples or genomes. "
                    "The first column must contain item names matching to those that are in your "
                    "input data. A different column should have the header 'group' and contain the "
                    "group name for each item. Each item should be associated with a single "
                    "group. It is always a good idea to define groups using single words without any fancy "
                    "characters. For instance, `HIGH_TEMPERATURE` or `LOW_FITNESS` are good group names. "
                    "`my group #1` or `IS-THIS-OK?`, are not good group names."}
                ),
    'sample-header': (
            ['--sample-header'],
            {'default': 'db_name',
            'help': "The header of the column containing your sample names in the modules-txt input file. By "
                    "default this is 'db_name' because we are assuming you got your modules mode output by "
                    "running `anvi-estimate-metabolism` in multi mode (on multiple genomes or metagenomes), but "
                    "just in case you got it a different way, this is how you can tell anvi'o which column to "
                    "look at. The values in this column should correspond to those in the 'sample' column in "
                    "the groups-txt input file."}
                ),
    'trnaseq-fasta': (
            ['-f', '--trnaseq-fasta'],
            {'metavar': 'FASTA',
             'required': False,
             'help': "The FASTA file containing merged (quality-controlled) tRNA-seq reads from a sample. "
                     "We recommend generating this file via `anvi-run-workflow -w trnaseq` "
                     "to ensure proper merging of read pairs that may be partially or fully overlapping, "
                     "and to automatically produce anvi'o-compliant simple deflines. "
                     "If there is a problem, anvi'o will gracefully complain about it."}
                ),
    'treatment': (
            ['--treatment'],
            {'default': 'untreated',
             'help': "The type of treatment applied during tRNA-seq sample preparation. "
                     "The values which are currently known to anvi'o are \"untreated\" and \"demethylase\", "
                     "as tRNA-seq samples are commonly split for these treatments. "
                     "Anvi'o will warn you if you do not choose one of these known options, but it will not affect data processing. "
                     "Treatment type is stored for further reference in the output tRNA-seq database, "
                     "and can be used in anvi-convert-trnaseq-database "
                     "to affect which nucleotides are called at predicted modification sites in tRNA seed sequences."}
                ),
    'write-checkpoints': (
            ['--write-checkpoints'],
            {'default': False,
             'action': 'store_true',
             'help': "Use this flag to write pickle files of intermediate results at key points in anvi-trnaseq. "
                     "If anvi'o crashes for some reason, the argument, --load-checkpoint, with the associated checkpoint name "
                     "can be used to restart the program from the given checkpoint. "
                     "This can be useful for saving time if anvi'o crashes "
                     "or in comparing the results of different advanced program parameterizations "
                     "involved in later stages of the analytical pipeline after the checkpoint, "
                     "such as --min-trna-fragment-size and --agglomeration-max-mismatch-freq. "
                     "This flag will overwrite existing intermediate files in the output directory as needed."}
                ),
    'load-checkpoint': (
            ['--load-checkpoint'],
            {'choices': ['profile', 'normalize', 'map_fragments'],
             'help': "Use this option to restart anvi-trnaseq from a checkpoint. "
                     "This can be useful for saving time if anvi'o crashed "
                     "or in comparing the results of different advanced program parameterizations "
                     "involved in later stages of the analytical pipeline after the checkpoint, "
                     "such as --min-trna-fragment-size and --agglomeration-max-mismatch-freq. "
                     "Use of this option requires that anvi-trnaseq was previously run with the flag, "
                     "--write-checkpoints, so that intermediate files were generated. "
                     "Checkpoint \"profile\" restarts after tRNA have been profiled and dereplicated. "
                     "\"normalize\" restarts after trimming and normalizing tRNA. "
                     "\"map_fragment\" restarts after unprofiled tRNA fragments have been mapped to normalized tRNA sequences. "
                     "To overwrite subsequent checkpoints after loading a checkpoint "
                     "(e.g., to overwrite \"map_fragment\" intermediate files after loading from \"normalize\"), "
                     "remember to also use the flag, --write-checkpoints."}
                ),
    'feature-param-file': (
            ['--feature-param-file'],
            {'metavar': 'FILE',
             'type': str,
             'help': "A .ini file can be provided to set tRNA feature parameters "
                     "used in de novo profiling/identification of tRNA sequences from the 3' end. "
                     "Generate the default file with the command, `anvi-trnaseq --default-feature-param-file`. "
                     "Dashes in the default file show parameters that cannot be changed, "
                     "because they do not exist or are set in stone. "
                     "For instance, the program only detects base pairing in stems, "
                     "so only stem features are parameterized with a maximum allowed number of unpaired nucleotides, "
                     "while every other feature has a dash in the \"Number allowed unpaired\" column. "
                     "Two quotes in the default file show parameters that are not currently set. "
                     "To lift a constraint, a parameter value can be replaced by \"\". "
                     "For instance, the conserved purine at D loop/position 21 indicated by the value, 0,R, "
                     "can be replaced by \"\" to prevent the program from seeking a conserved nucleotide there. "
                     "Conserved nucleotides in a feature are set by pairs of zero-based indices and nucleotide symbols. "
                     "The index indicates the conserved position in the feature, relative to the 5' end of the feature. "
                     "The nucleotide symbol can be A, C, G, T (U in cDNA), R (purine), or Y (pyrimidine). "
                     "The index is separated from the symbol by a comma. "
                     "Multiple conserved positions in a feature are separted by a semicolon. "
                     "Feature profiling of a sequence halts when the number of allowed unconserved nucleotides in a feature "
                     "or the number of allowed unpaired positions in a stem is exceeded. "
                     "The default allowed number of unconserved nucleotides in the D loop, for example, is 1, "
                     "so 4 of the 5 conserved positions must be found for the D loop to be positively identified. "
                     "By default, 1 position is allowed to be unpaired (no Watson-Crick or G-T wobble base pair) "
                     "in each of the 4 stems; the user could, for instance, "
                     "lift this constraint on the acceptor stem by changing the value from 1 to \"\". "
                     "There are 3 variable-length sections of tRNA. The user could, for example, "
                     "change the allowed lengths of the V loop from a discontinuous range, \"4-5,9-23\", to a continuous range, \"4-23\"."}
                ),
    'threeprime-termini': (
            ['--threeprime-termini'],
            {'default': 'CCA,CC,C,CCAN,CCANN',
             'type': str,
             'help': "Termini represent the subsequences (in the 5'->3' orientation) "
                     "to expect at the 3' end of a tRNA read adjacent to the discriminator nucleotide. "
                     "tRNA feature profiling from the 3' end seeks a valid terminus prior to the discriminator and more 5' features. "
                     "3' terminal sequences can include the nucleotides, A, C, G, and T, and N, symbolizing any nucleotide. "
                     "A single underscore, \"_\", can be included in lieu of a sequence, "
                     "symbolizing the absence of a terminus such that the tRNA feature profile may end with the discriminator. "
                     "If \"_\" is not included, tRNA sequences ending in the discriminator will still be sought as *fragments* of profiled tRNA. "
                     "The order of sequences in the argument is the order of consideration in profiling. "
                     "For example, if CCA is the first 3' terminus considered, "
                     "and it produces a complete profile with no unconserved or unpaired nucleotides, then the other possible termini are not considered. "
                     "Other termini are only considered with the possibility of \"improvement\" in the feature profile."}
                ),
    'min-length-long-fiveprime': (
            ['--min-length-long-fiveprime'],
            {'default': 4,
             'metavar': 'INT',
             'type': int,
             'help': "tRNA reads often extend beyond the 5' end of a mature tRNA sequence. "
                     "This can be biological in origin when the read is from pre-tRNA; artifactual in origin "
                     "when the reverse transcriptase runs off the end of the template, adding a small number ofs random bases; "
                     "or artifactual when the read is a chimera of tRNA at the 3' end and another, potentially non-tRNA, transcript at the 5' end. "
                     "Longer 5' extensions are more likely to be biological than artifactual due to the exclusion of runoff bases. "
                     "This parameter sets the minimum length of 5' sequence extensions "
                     "that are recorded in the tRNA-seq database output for further analysis."}
                ),
    'min-trna-fragment-size': (
            ['--min-trna-fragment-size'],
            {'default': 25,
             'metavar': 'INT',
             'type': int,
             'help': "Anvi'o profiles a sequence as tRNA by identifying tRNA features from the 3' end of the sequence. "
                     "tRNA-seq datasets can include a significant number of tRNA fragments "
                     "that are not from the 3' end of the sequence ending in a recognized terminus, e.g., CCA. "
                     "These \"interior\" and 5' fragments can be of significant biological interest. "
                     "Fragments are identified by mapping unprofiled reads to profiled tRNAs that have their 3' termini trimmed off. "
                     "This parameter sets the minimum length of unprofiled reads searched in this manner. "
                     "The choice of %(default)d as the default value is motivated by considerations "
                     "of false positive matches and computational performance with a shorter minimum sequence length. "
                     "Since unprofiled reads are mapped to every unique profiled tRNA sequence, "
                     "a shorter minimum sequence length can make mapping take a very long time "
                     "and return too many alignments to store in memory for datasets of millions of reads. "
                     "Pay attention to python memory usage if you adjust this parameter downwards."}
                ),
    'agglomeration-max-mismatch-freq': (
            ['--agglomeration-max-mismatch-freq'],
            {'default': 2/71,
             'metavar': 'FLOAT',
             'type': float,
             'help': "Anvi'o finds potential tRNA modifications by first agglomerating sequences "
                     "differing from one or more other sequences in the cluster by mismatches at a certain fraction of nucleotides. "
                     "This parameter sets the maximum mismatch fraction that is allowed, by default 2/71. "
                     "This number represents 2 mismatches in a full-length tRNA of length 74, not 71, "
                     "as 3' sequence variants, including the canonical 3'-CCA, are trimmed off prior to sequences being agglomerated. "
                     "(Average non-mitochondrial tRNAs range in length from 74-95.) "
                     "For example, consider 3 trimmed sequences of length 71 -- A, B and C -- and 1 sequence of length 70, D. "
                     "If A differs from B by a substitution at position 1, and C differs from B at positions 10 and 20, "
                     "such that C differs from A by 3 substitutions, then A, B, and C will still agglomerate into a single cluster, "
                     "as each differs by no more than 2 substitutions from some other sequence in the cluster. "
                     "In contrast, sequence D differs from B at positions 30 and 40, "
                     "exceeding the 2/71 fraction required to agglomerate (2/70 > 2/71), "
                     "so D forms its own cluster and is not consolidated into a single modified sequence with the others."}
                ),
    'fiveprimemost-deletion-start': (
            ['--fiveprimemost-deletion-start'],
            {'default': -2,
             'metavar': 'INT',
             'type': int,
             'help': "The 5'-most position relative to a potential modified nucleotide at which prospective deletions can begin. "
                     "The default value of -2 means deletions can start at most 2 nucleotides 5' of a modification. "
                     "Logically, the parameter value must be less than or equal to the value of --threeprimemost-deletion-start "
                     "and less than or equal to the value of --fiveprimemost-deletion-stop."}
                ),
    'threeprimemost-deletion-start': (
            ['--threeprimemost-deletion-start'],
            {'default': 0,
             'metavar': 'INT',
             'type': int,
             'help': "The 3'-most position relative to a potential modified nucleotide at which prospective deletions can begin. "
                     "The default value of 0 means the 3'-most start position of a deletion is the modification site itself. "
                     "Logically, the parameter value must be greater than or equal to the value of --fiveprimemost-deletion-start "
                     "and less than or equal to the value of --threeprimemost-deletion-stop."}
                ),
    'fiveprimemost-deletion-stop': (
            ['--fiveprimemost-deletion-stop'],
            {'default': -1,
             'metavar': 'INT',
             'type': int,
             'help': "The 5'-most position relative to a potential modified nucleotide at which prospective deletions can end. "
                     "The default value of -1 means deletions can end at most 1 nucleotide 5' of a modification. "
                     "Logically, the parameter value must be greater than or equal to the value of --fiveprimemost-deletion-start "
                     "and less than or equal to the value of --threeprimemost-deletion-stop."}
                ),
    'threeprimemost-deletion-stop': (
            ['--threeprimemost-deletion-stop'],
            {'default': 0,
             'metavar': 'INT',
             'type': int,
             'help': "The 3'-most position relative to a potential modified nucleotide at which prospective deletions can end. "
                     "The default value of 0 means the 3'-most stop position of a deletion is the modification site itself. "
                     "Logically, the parameter value must be greater than or equal to the value of --threeprimemost-deletion-start "
                     "and greater than or equal to the value of --fiveprimemost-deletion-stop."}
                ),
    'max-distinct-deletions': (
            ['--max-distinct-deletions'],
            {'default': 2,
             'metavar': 'INT',
             'type': int,
             'help': "The maximum number of distinct deletions -- which can be of varying size -- "
                     "that can be introduced around potential modifications in the search for deletions. "
                     "Higher values of this parameter may lead to identification of more deletions (at the expense of runtime). "
                     "For example, with the default value of 2 and a sequence containing 3 potential substitutions positions, "
                     "then some in silico template sequences will be produced containing deletions around the first position; "
                     "others will be produced containing deletions at the first and second positions; "
                     "the first and third positions; the second position; the second and third; and the third."}
                ),
    'min-distance-between-deletions': (
            ['--min-distance-between-deletions'],
            {'default': 4,
             'metavar': 'INT',
             'type': int,
             'help': "The minimum number of nucleotides that must exist between distinct deletions "
                     "introduced around potential modifications in the search for deletions. "
                     "There is often a \"smear\" of associated substitutions around the main substitution site at a modified nucleotide. "
                     "In silico deletions introduced around nearby substitutions in this smear "
                     "can produce unconstrained, potentially erroneous matches to the search pool of sequences that may be tRNA with deletions. "
                     "Separation of in silico deletions using this parameter quashes this problem. "
                     "The default value was determined by inspection of deletions predicted from large datasets. "
                     "It is hard to envision a case where the user would adjust this parameter downward."}
                ),
    'max-deletion-configurations': (
            ['--max-deletion-configurations'],
            {'default': 10000,
             'metavar': 'INT',
             'type': int,
             'help': "The maximum number of in silico sequences with distinct configurations of deletions "
                     "that can be generated from a single sequence with potential modifications. "
                     "There is often a \"smear\" of associated substitutions around the main substitution site at a modified nucleotide. "
                     "Sometimes, this effect manifests over a majority of nucleotides in the tRNA, "
                     "producing a vast number of configurations of in silico deletions that can take forever to search -- "
                     "especially when multiple deletions are allowed in a single sequence (set by --max-distinct-deletions), "
                     "and deletions can be of varying lengths (set by --fiveprimemost-deletion-start/stop and --threeprimemost-deletion-start/stop). "
                     "If a template sequence spawns more sequences with in silico deletions than this parameter allows, "
                     "the maximum number of distinct deletions, the parameter with the biggest effect, "
                     "is decremented for the sequence and in silico deletions are again introduced."}
                ),
    'skip-fasta-check': (
            ['--skip-fasta-check'],
            {'default': False,
             'action': 'store_true',
             'help': "Don't check the input FASTA file for such things as proper defline formatting to speed things up."}
                ),
    'profiling-chunk-size': (
            ['--profiling-chunk-size'],
            {'default': 500000,
             'metavar': 'INT',
             'type': int,
             'help': "Anvi'o manages memory consumption during tRNA feature profiling by chunking the unique input sequences. "
                     "This parameter sets the maximum number of sequences in each chunk. "
                     "Adjustment of this parameter has little effect on speed."}
                ),
    'alignment-target-chunk-size': (
            ['--alignment-target-chunk-size'],
            {'default': 25000,
             'metavar': 'INT',
             'type': int,
             'help': "Anvi'o sequence alignment manages memory consumption by chunking the list of alignment targets, "
                     "so that queries are aligned to the first chunk of targets, then the second chunk, and so on. "
                     "This parameter sets the maximum number of target sequences in each chunk. "
                     "Memory management becomes important when aligning short queries to a large number of targets, "
                     "which involves searching queries against a massive number of k-mers "
                     "(equal in length to the shortest query) that have been extracted from targets. "
                     "Adjust this parameter downward if your system runs out of memory during alignment; "
                     "adjust this parameter upward to speed up alignment if you find that you are not memory-limited. "
                     "Ideally, we would set this parameter using a heuristic function "
                     "parameterized with the numbers and lengths of query and target sequences..."}
                ),
    'fragment-mapping-query-chunk-length': (
            ['--fragment-mapping-query-chunk-length'],
            {'default': 20,
             'metavar': 'INT',
             'type': int,
             'help': "Mapping potential tRNA fragments to profiled tRNA can generate massive data structures. "
                     "To manage memory consumption, the fragment queries are chunked and run as separate alignment tasks. "
                     "Queries are chunked based on sequence length, as longer k-mers can be used with longer queries to speed up mapping. "
                     "This parameter sets the sequence length interval used to chunk queries. "
                     "For a standard tRNA-seq dataset with --min-trna-fragment-size set to the default of 25 "
                     "and a maximum unprofiled query length of, say, 170, "
                     "the default length interval would result in 8 chunks: 25-44 nts, 45-64 nts, etc. "
                     "Adjust this parameter downward if your system runs out of memory during alignment; "
                     "adjust this parameter upward to speed up alignment if you find that you are not memory-limited. "
                     "Ideally, we would set this parameter using a heuristic function "
                     "parameterized with the numbers and lengths of query and target sequences..."}
                ),
    'profiling-progress-interval': (
            ['--profiling-progress-interval'],
            {'default': 500000,
             'metavar': 'INT',
             'type': int,
             'help': "Progress in the tRNA feature profiling of unique input sequences "
                     "is reported after a certain number of sequences have been processed."}
                ),
    'fragment-filter-progress-interval': (
            ['--fragment-filter-progress-interval'],
            {'default': 50000,
             'metavar': 'INT',
             'type': int,
             'help': "Progress is reported after a certain number of unprofiled sequence queries have been processed "
                     "during the filtering of matches between these sequences and profiled tRNA. "
                     "This filtering step is part of the search for biological tRNA fragments."}
                ),
    'alignment-progress-interval': (
            ['--alignment-progress-interval'],
            {'default': 500000,
             'metavar': 'INT',
             'type': int,
             'help': "Progress is reported after a certain number of queries have been processed "
                     "in mapping unprofiled sequences to profiled tRNA to find interior and 5' tRNA fragments "
                     "and in mapping sequences to each other in agglomeration, a stage in the identification of modifications."}
                ),
    'modification-progress-interval': (
            ['--modification-progress-interval'],
            {'default': 10000,
             'metavar': 'INT',
             'type': int,
             'help': "Progress in identifying modifications is reported after a certain number of sequences have been processed. "
                     "Progress is reported in two distinct stages of this process, "
                     "sequence agglomeration and cluster decomposition, with the same interval used in each."}
                ),
    'default-feature-param-file': (
            ['--default-feature-param-file'],
            {'metavar': 'OUTPUT_FILENAME',
             'type': str,
             'help': "Writes a tab-delimited .ini file containing default tRNA feature parameterizations "
                     "used in de novo profiling/identification of tRNA sequences from the 3' end. "
                     "Parameters can be modified by the user and the file fed back into anvi-trnaseq "
                     "through the --feature-param-file argument, the help description of which explains the file format."}
                ),
    'print-default-feature-params': (
            ['--print-default-feature-params'],
            {'default': False,
             'action': 'store_true',
             'help': "Prints to standard output a nicely formatted table of the default tRNA feature parameterizations "
                     "(which can be written to a tab-delimited .ini file by the option, --default-feature-param-file)."}
                ),
    'max-reported-trna-seeds': (
            ['--max-reported-trna-seeds'],
            {'default': 10000,
             'metavar': 'INT',
             'type': int,
             'help': "This parameter limits the number of tRNA seed sequences reported in the contigs database, "
                     "as anvi-interactive can have trouble displaying large numbers of items. "
                     "To remove the limit on reported seeds, specify a value of -1."}
                ),
    'feature-threshold': (
            ['--feature-threshold'],
            {'default': 'anticodon_loop',
             'type': str,
             'choices': constants.TRNA_SEED_FEATURE_THRESHOLD_CHOICES,
             'help': "This option prevents formation of tRNA seed sequences from input sequences "
                     "that did not reach the threshold feature in anvi-trnaseq profiling from the 3' end. "
                     "The more stringent the threshold, the fewer spurious seeds are formed "
                     "from rare chimeric and other inaccurate tRNA predictions. "
                     "The most stringent threshold is \"acceptor_stem\", the most 5' feature, "
                     "resulting in seeds formed only from tRNAs with a complete feature set "
                     "(with the exception of the extra 5'-G in tRNA-His)."}
                ),
    'preferred-treatment': (
            ['--preferred-treatment'],
            {'type': str,
             'help': "tRNA-seq databases recorded as employing the preferred treatment are given preference "
                     "in setting nucleotides at predicted modification positions in tRNA seed sequences. "
                     "By default, equal preference is given to all of the input databases. "
                     "The reason for this parameter is that paired untreated and enzymatically treated splits "
                     "can assist in the identification of underlying modified nucleotides. "
                     "For example, splits treated with a demethylase can be compared to untreated splits "
                     "to probe which nucleotides are methylated."}
                ),
    'nonspecific-output': (
            ['--nonspecific-output'],
            {'default': 'nonspecific_db,combined_db',
             'type': str,
             'help': "A significant fraction of tRNA-seq reads can be from tRNA fragments. "
                     "These can be real biomolecules or artifactual 3' fragments "
                     "produced as a result of incomplete reverse transcription of the tRNA template to cDNA. "
                     "Rather than randomly assigning fragments to a single target, "
                     "as in metagenomic read recruitment by Bowtie, "
                     "anvi-trnaseq tracks all of the longer sequences containing each fragment. "
                     "This results in two categories of coverage: "
                     "'specific' for reads that are only found in one seed "
                     "and 'nonspecific' for reads found in multiple seeds. "
                     "Specific coverages are always reported in a separate profile database. "
                     "Nonspecific coverages can be reported in three types of database, as specified by this parameter. "
                     "'nonspecific_db' produces a profile database only containing nonspecific coverages. "
                     "'combined_db' produces a database containing separate specific and nonspecific layers. "
                     "'summed_db' produces a database containing summed specific and nonspecific coverages. "
                     "To produce multiple types of databases, separate the database types with commas (no spaces). "
                     "For example, all three databases are produced with the argument, 'nonspecific_db,combined_db,summed_db'."}
                ),
    'min-variation': (
            ['--min-variation'],
            {'default': 0.01,
             'metavar': 'FLOAT',
             'type': float,
             'help': "When more than 2 nucleotides are found at a position in a tRNA, "
                     "a modification-induced mutation (substitution) is considered rather than a single nucleotide variant. "
                     "This parameter sets a key criterion for the prediction of a modification, "
                     "the minimum fraction of specific coverage at a position with more than 2 nucleotides "
                     "that must be contributed by nucleotides beside the most abundant nucleotide. "
                     "For example, if A, C, and G are found at position 20 of a tRNA, "
                     "and A is represented by 95 reads, C by 3 reads, and G by 1 read, then with a parameter value of 0.05, "
                     "the site would be 1 C, G, or T short of meeting the threshold for prediction of a modification."}
                ),
    'min-third-fourth-nt': (
            ['--min-third-fourth-nt'],
            {'default': 0.002,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This parameter sets a key criterion for the prediction of a modification, "
                     "the minimum fraction of specific coverage at a position with more than 2 nucleotides "
                     "that must be contributed by nucleotides beside the 2 most abundant nucleotides. "
                     "Unlike --min-variation, this criterion only needs to be met for 1 sample "
                     "to permit modification of the position in all samples of the experiment. "
                     "For example, consider an experiment with 2 samples and a parameter value of 0.01. "
                     "In Sample 1, A, C, and G are found at position 20 of a tRNA, "
                     "and A is represented by 95 reads, C by 4 reads, and G by 1 read. "
                     "The default parameter value of 0.01 is exactly met at the position thanks to G. "
                     "In Sample 2, A, C, G, and T are found at position 20 of the same tRNA seed, "
                     "and A is represented by 1000 reads, C by 100 reads, G by 2 reads, and T by 2 reads. "
                     "The third and fourth nucleotides don't meet the coverage threshold of 0.01, "
                     "but this is irrelevant for calling the modification, since Sample 1 met the criterion. "
                     "There is an important consideration due to the way this threshold is currently imposed. "
                     "Potential modification sites that do not meet the threshold "
                     "are not treated like single nucleotide variants in anvi-trnaseq: "
                     "they do not cause the seed sequence to be split "
                     "such that no seed contains a variant that was not deemed to be a modification. "
                     "Rather, candidate modification positions that do not meet this threshold "
                     "are retained in the seed BUT NOT REPORTED. "
                     "Therefore, we recommend rerunning this command with a parameter value of 0 "
                     "to inspect seeds for undisplayed variants (possible SNVs) "
                     "with a low level of third and fourth nucleotides."}
                ),
    'min-deletion-fraction': (
            ['--min-deletion-fraction'],
            {'default': 0.002,
             'metavar': 'FLOAT',
             'type': float,
             'help': "This parameter controls which deletions are reported in the tRNA-seq profile database. "
                     "Coverage of a deletion in a sample must meet the minimum fraction of specific coverage. "
                     "Deletion coverages are calculated separately for specific, nonspecific, and summed coverages."}
    )
}

# two functions that works with the dictionary above.
def A(param_id, exclude_param=None):
    if exclude_param:
        return [p for p in D[param_id][0] if p != exclude_param]
    else:
        return D[param_id][0]

def K(param_id, params_dict={}):
    kwargs = copy.deepcopy(D[param_id][1])
    for key in params_dict:
        kwargs[key] = params_dict[key]

    return kwargs

# The rest of this file is composed of code that responds to '-v' or '--version' calls from clients,
# and provides access to the database version numbers for all anvi'o modules.

import anvio.tables as t
from anvio.terminal import Run


run = Run()


def set_version():
    return anvio_version, \
           anvio_codename, \
           t.contigs_db_version, \
           t.pan_db_version, \
           t.profile_db_version, \
           t.genes_db_version, \
           t.auxiliary_data_version, \
           t.genomes_storage_vesion, \
           t.structure_db_version, \
           t.metabolic_modules_db_version, \
           t.trnaseq_db_version


def get_version_tuples():
    return [("Anvi'o version", "%s (v%s)" % (__codename__, __version__)),
            ("Profile DB version", __profile__version__),
            ("Contigs DB version", __contigs__version__),
            ("Genes DB version", __genes__version__),
            ("Auxiliary data storage version", __auxiliary_data_version__),
            ("Pan DB version", __pan__version__),
            ("Genome data storage version", __genomes_storage_version__),
            ("Structure DB version", __structure__version__),
            ("KEGG Modules DB version", __kegg_modules_version__),
            ("tRNA-seq DB version", __trnaseq__version__)]


def print_version():
    run.info("Anvi'o", "%s (v%s)" % (__codename__, __version__), mc='green', nl_after=1)
    run.info("Profile database", __profile__version__)
    run.info("Contigs database", __contigs__version__)
    run.info("Pan database", __pan__version__)
    run.info("Genome data storage", __genomes_storage_version__)
    run.info("Auxiliary data storage", __auxiliary_data_version__)
    run.info("Structure database", __structure__version__)
    run.info("Metabolic modules database", __kegg_modules_version__)
    run.info("tRNA-seq database", __trnaseq__version__, nl_after=1)


__version__, \
__codename__, \
__contigs__version__, \
__pan__version__, \
__profile__version__, \
__genes__version__, \
__auxiliary_data_version__, \
__genomes_storage_version__ , \
__structure__version__, \
__kegg_modules_version__, \
__trnaseq__version__ = set_version()


if '-v' in sys.argv or '--version' in sys.argv:
    print_version()
    sys.exit()

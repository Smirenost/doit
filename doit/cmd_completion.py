"""generate shell script with tab complention code for doit commands/tasks"""

import sys
from string import Template

from .cmd_base import DoitCmdBase


opt_shell = {
    'name': 'shell',
    'short': 's',
    'long': 'shell',
    'type': str,
    'default': 'bash',
    'help': 'Completion code for SHELL. default: "bash". options: [bash, zsh]',
    }

opt_hardcode_tasks = {
    'name': 'hardcode_tasks',
    'short': '',
    'long': 'hardcode-tasks',
    'type': bool,
    'default': False,
    'help': 'Hardcode tasks from current task list.',
    }



class TabCompletion(DoitCmdBase):
    """generate scripts for tab-completion

    If hardcode-tasks options is chosen it will get the task
    list from the current dodo file and include in the completion script.
    Otherwise the script will dynamically call `doit list` to get the list
    of tasks.

    If it is completing a sub-task (contains ':' in the name),
    it will always call doit while evaluating the options.

    """
    doc_purpose = "generate script for tab-complention"
    doc_usage = ""
    doc_description = None

    cmd_options = (opt_shell, opt_hardcode_tasks, )

    def execute(self, opt_values, pos_args):
        if opt_values['shell'] == 'bash':
            self._generate_bash(opt_values, pos_args)
        elif opt_values['shell'] == 'zsh':
            self._generate_zsh(opt_values, pos_args)
        else:
            print('Invalid option')


    def _generate_bash(self, opt_values, pos_args):
        # some applications built with doit do not use dodo.py files
        for opt in self.options:
            if opt.name=='dodoFile':
                get_dodo_part = bash_get_dodo
                pt_list_param = '--file="$dodof"'
                break
        else:
            get_dodo_part = ''
            pt_list_param = ''

        # dict with template values
        pt_bin_name = sys.argv[0].split('/')[-1]
        tmpl_vars = {
            'pt_bin_name': pt_bin_name,
            'pt_cmds': ' '.join(self.doit_app.sub_cmds),
            'pt_list_param': pt_list_param,
            }

        # if hardcode tasks
        if opt_values['hardcode_tasks']:
            self.task_list, self.config = self._loader.load_tasks(
                self, opt_values, pos_args)
            tmpl_vars['pt_tasks'] = '"{}"'.format(
                ' '.join(t.name for t in self.task_list if not t.is_subtask))
        else:
            tmpl_list_cmd = "$({} list {} --quiet 2>/dev/null)"
            tmpl_vars['pt_tasks'] = tmpl_list_cmd.format(pt_bin_name,
                                                         pt_list_param)

        template = Template(bash_start + bash_opt_file + get_dodo_part +
                            bash_task_list + bash_end)
        self.outstream.write(template.safe_substitute(tmpl_vars))


    @staticmethod
    def _zsh_arg_line(opt):
        """create a text line for completion of a command arg"""
        # '(-c|--continue)'{-c,--continue}'[continue executing tasks...]' \
        # '--db-file[file used to save successful runs]' \
        if opt.short and opt.long:
            tmpl = ("'(-{0.short}|--{0.long})'{{-{0.short}, --{0.long}}}'"
                    "[{0.help}]' \ ")
        elif not opt.short and opt.long:
            tmpl = "'--{0.long}[{0.help}]' \ "
        elif opt.short and not opt.long:
            tmpl = "'-{0.short}[{0.help}]' \ "
        else: # without short or long options cant be really used
            return ''
        return tmpl.format(opt).replace('\n', ' ')


    @staticmethod
    def _zsh_cmd_args(cmd, arg_lines):
        """create the content for "case" statement with all command options """
        tmpl = """    {cmd_name})
     _command_args=(
      {args_body}
    )
    ;;
"""
        args_body = '\n      '.join(arg_lines)
        return tmpl.format(cmd_name=cmd.name, args_body=args_body)


    def _generate_zsh(self, opt_values, pos_args):
        # # some applications built with doit do not use dodo.py files
        # for opt in self.options:
        #     if opt.name=='dodoFile':
        #         get_dodo_part = bash_get_dodo
        #         pt_list_param = '--file="$dodof"'
        #         break
        # else:
        #     get_dodo_part = ''
        #     pt_list_param = ''

        cmds_desc = []
        cmds_args = []
        for cmd in self.doit_app.sub_cmds.values():
            cmds_desc.append("    '{}: {}'".format(cmd.name, cmd.doc_purpose))
            args = []
            for opt in cmd.options:
                args.append(self._zsh_arg_line(opt))
            cmds_args.append(self._zsh_cmd_args(cmd, args))

        template_vars = {
            'pt_bin_name': sys.argv[0].split('/')[-1],
            'pt_cmds': '\n'.join(cmds_desc),
            'pt_cmds_args': '\n'.join(cmds_args),
        #     'pt_list_param': pt_list_param,
        }

        # if opt_values['hardcode_tasks']:
        #     self.task_list, self.config = self._loader.load_tasks(
        #         self, opt_values, pos_args)
        #     template_vars['pt_tasks'] = '"{}"'.format(
        #         ' '.join(t.name for t in self.task_list if not t.is_subtask))
        # else:
        #     tmpl_tasks = Template("$($pt_bin_name list $pt_list_param --quiet 2>/dev/null)")
        #     template_vars['pt_tasks'] = tmpl_tasks.safe_substitute(template_vars)

        template = Template(zsh_start)
        self.outstream.write(template.safe_substitute(template_vars))




############## templates
# Variables starting with 'pt_' belongs to the Python Template
# to generate the script.
# Remaining are shell variables used in the script.


################################################################
############### bash template


bash_start = """# bash completion for $pt_bin_name
# auto-generate by `$pt_bin_name tabcomplention`

# to activate it you need to 'source' the generate script
# $ source <generated-script>

# reference => http://www.debian-administration.org/articles/317
# patch => http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=711879

_$pt_bin_name()
{
    local cur prev words cword basetask sub_cmds tasks i dodof
    COMPREPLY=() # contains list of words with suitable completion
    # remove colon from word separator list because doit uses colon on task names
    _get_comp_words_by_ref -n : cur prev words cword
    # list of sub-commands
    sub_cmds="$pt_cmds"

"""

# FIXME - wont be necessary after adding support for options with type
bash_opt_file = """
    # options that take file/dir as values should complete file-system
    if [[ "$prev" == "-f" || "$prev" == "-d" || "$prev" == "-o" ]]; then
        _filedir
        return 0
    fi
    if [[ "$cur" == *=* ]]; then
        prev=${cur/=*/}
        cur=${cur/*=/}
        if [[ "$prev" == "--file=" || "$prev" == "--dir=" || "$prev" == "--output-file=" ]]; then
            _filedir -o nospace
            return 0
        fi
    fi

"""


bash_get_dodo = """
    # get name of the dodo file
    for (( i=0; i < ${#words[@]}; i++)); do
        case "${words[i]}" in
        -f)
            dodof=${words[i+1]}
            break
            ;;
        --file=*)
            dodof=${words[i]/*=/}
            break
            ;;
        esac
    done
    # dodo file not specified, use default
    if [ ! $dodof ]
      then
         dodof="dodo.py"
    fi

"""

bash_task_list = """
    # get task list
    # if it there is colon it is getting a subtask, complete only subtask names
    if [[ "$cur" == *:* ]]; then
        # extract base task name (remove everything after colon)
        basetask=${cur%:*}
        # sub-tasks
        tasks=$($pt_bin_name list $pt_list_param --quiet --all ${basetask} 2>/dev/null)
        COMPREPLY=( $(compgen -W "${tasks}" -- ${cur}) )
        __ltrim_colon_completions "$cur"
        return 0
    # without colons get only top tasks
    else
        tasks=$pt_tasks
    fi

"""

bash_end = """
    # match for first parameter must be sub-command or task
    # FIXME doit accepts options "-" in the first parameter but we ignore this case
    if [[ ${cword} == 1 ]] ; then
        COMPREPLY=( $(compgen -W "${sub_cmds} ${tasks}" -- ${cur}) )
        return 0
    fi

    # if command is help complete with tasks or sub-commands
    if [[ ${words[1]} == "help" ]] ; then
        COMPREPLY=( $(compgen -W "${sub_cmds} ${tasks}" -- ${cur}) )
        return 0
    fi

    # if there is already one parameter match only tasks (no commands)
    COMPREPLY=( $(compgen -W "${tasks}" -- ${cur}) )

}
complete -F _$pt_bin_name $pt_bin_name
"""



################################################################
############### zsh template


zsh_start = """
#compdef _$pt_bin_name

local -a _1st_arguments
_1st_arguments=(
$pt_cmds
   )

_arguments '*:: :->command'

if (( CURRENT == 1 )); then
   _describe -t commands "_$pt_bin_name command" _1st_arguments
   return
fi

local -a _command_args
case "$words[1]" in
  $pt_cmds_args
esac

_arguments $_command_args && return 0
"""

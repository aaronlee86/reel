import sys
import argparse
import subprocess
import threading
import queue

def stream_output(pipe, output_queue, is_text=False):
    """
    Stream output from a subprocess pipe.

    Args:
        pipe (file): The pipe to read from
        output_queue (queue.Queue): Queue to store output lines
        is_text (bool): Whether the pipe is in text mode
    """
    try:
        if is_text:
            # If already in text mode, read directly
            for line in iter(pipe.readline, ''):
                output_queue.put(line.rstrip())
        else:
            # If in bytes mode, decode
            for line in iter(pipe.readline, b''):
                output_queue.put(line.decode('utf-8', errors='replace').rstrip())
        pipe.close()
    except Exception as e:
        print(f"Error in stream_output: {e}")

def run_scripts(scripts, parameter=None, max_stage=None, specific_stage=None):
    """
    Run a list of Python scripts sequentially with real-time output.

    Args:
        scripts (list): List of script paths to run
        parameter (str, optional): Parameter to pass to each script
        max_stage (int, optional): Maximum number of scripts to run
        specific_stage (int, optional): Specific script stage to run

    Returns:
        bool: True if all scripts run successfully, False otherwise
    """
    # Determine which scripts to run
    if specific_stage is not None:
        # Adjust for 1-based indexing
        scripts_to_run = [scripts[specific_stage - 1]] if 0 < specific_stage <= len(scripts) else []
    elif max_stage is not None:
        scripts_to_run = scripts[:max_stage]
    else:
        scripts_to_run = scripts

    for script in scripts_to_run:
        try:
            # Prepare the command with optional parameter
            cmd = [sys.executable, script]
            if parameter is not None:
                cmd.append(parameter)

            # Start the subprocess with pipes
            print(f"\n{'='*40}")
            print(f"Running: {' '.join(cmd)}")
            print(f"{'='*40}")

            # Determine text mode based on Python version
            text_mode = sys.version_info >= (3, 7)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=text_mode,
                encoding='utf-8' if text_mode else None
            )

            # Create queues for stdout and stderr
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()

            # Create threads for streaming output
            stdout_thread = threading.Thread(
                target=stream_output,
                args=(process.stdout, stdout_queue, text_mode)
            )
            stderr_thread = threading.Thread(
                target=stream_output,
                args=(process.stderr, stderr_queue, text_mode)
            )

            # Start the threads
            stdout_thread.start()
            stderr_thread.start()

            # Print output in real-time
            while stdout_thread.is_alive() or stderr_thread.is_alive() or not stdout_queue.empty() or not stderr_queue.empty():
                # Print stdout
                try:
                    while True:
                        line = stdout_queue.get_nowait()
                        print(f"STDOUT: {line}")
                except queue.Empty:
                    pass

                # Print stderr
                try:
                    while True:
                        line = stderr_queue.get_nowait()
                        print(f"STDERR: {line}")
                except queue.Empty:
                    pass

            # Wait for the process to complete
            return_code = process.wait()

            # Wait for output threads to finish
            stdout_thread.join()
            stderr_thread.join()

            # Check return code
            if return_code != 0:
                print(f"\nScript {script} failed with return code {return_code}")
                return False

        except Exception as e:
            print(f"Error running {script}: {e}")
            return False

    return True

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run a sequence of Python scripts')
    parser.add_argument('--max-stage',
                        type=int,
                        help='Maximum number of scripts to run',
                        default=None)
    parser.add_argument('--stage',
                        type=int,
                        help='Specific script stage to run (1-based indexing)',
                        default=None)
    parser.add_argument('parameter',
                        nargs='?',
                        help='Parameter to pass to each script',
                        default=None)

    # List of scripts to run in order
    scripts_to_run = [
        'script2scene.py',
        'scene2v.py',
        'v2tts.py',
        'tts2clips.py',
        'event_runner.py'
    ]

    # Parse arguments
    args = parser.parse_args()

    # Validate argument combinations
    if args.max_stage is not None and args.stage is not None:
        parser.error("Cannot specify both --max-stage and --stage")

    # Run the scripts
    success = run_scripts(scripts_to_run,
                          parameter=args.parameter,
                          max_stage=args.max_stage,
                          specific_stage=args.stage)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
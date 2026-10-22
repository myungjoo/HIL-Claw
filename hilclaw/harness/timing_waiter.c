/*
 * The waiter: process 1 of the container of a timing process (ADR-0145
 * decision 3, code slice (5)).
 *
 * The timing process container starts this program in place of the timing
 * executable. It starts that executable as its one child, waits for it, ends
 * every other process of its PID namespace and then writes one last line with
 * the child's raw ru_maxrss. It is one translation unit that includes only
 * system headers, and it builds under -std=c99 and under the flags of ADR-0116
 * decision 3 (-std=gnu11 -O2 -ffp-contract=off).
 *
 * Command line: <timing executable path> <argument>...
 * argv[1] is the path (no PATH search) and argv[1..] the child's argument
 * vector. No standard input, file or environment variable is read.
 *
 * Steps, in order; a step that fails ends the waiter at once and no later
 * step is done, so a waiter's line always means that its child was started
 * and waited for:
 *   W0  its process id is not 1: it starts nothing and writes nothing on
 *       standard output.
 *   W1  prctl(PR_SET_DUMPABLE, 0); no signal handler is established anywhere.
 *   W2  fork and execv argv[1] with argv[1..]; the environment, the working
 *       directory, standard output and standard error are handed on as given.
 *       An executable that cannot be started is a started child that ends
 *       with status 127, so its line is written.
 *   W3  wait4 on that child's pid only (never -1: orphans are children of
 *       process 1 too), retried on EINTR; its ru_maxrss is kept.
 *   W4  kill(-1, SIGKILL) and waitpid(-1, ...), sending again after each
 *       reaped child, until ECHILD.
 *   W5  O_NONBLOCK is cleared on descriptor 1, then "\n" and the line are
 *       written with write(2) until every byte is written or a write fails.
 *       No memory is allocated and no stdio is used from W3 to W5.
 *   W6  the exit status below.
 *
 * The line, as hilclaw/standin_waiter_line.py reads it, ASCII and ended by
 * one LF: "waiter_max_rss_kib <v>", <v> being the raw ru_maxrss as
 * printf("%ld") writes it, where compiled for Linux; "waiter_max_rss none"
 * otherwise. Off Linux, by this file's reading of ADR-0145 decisions 3 to 5
 * (there is no figure to protect), W1 only establishes no signal handler and
 * W0 only checks that the process id is 1.
 *
 * Exit status:
 *   0  the child exited by itself with status 0 and the line was written
 *   1  the child ended otherwise (non-zero status, a signal, or an executable
 *      that could not be started) and the line was written
 *   2  the command line has no executable path; nothing was started
 *   3  W0: the waiter is not process 1; nothing was started
 *   4  a system call of W1 to W5 failed; no line, or part of one
 * A status other than 0 and 1 comes with one line on standard error. The
 * waiter compares nothing, is handed no bound and decides no tool answer
 * (ADR-0145 decisions 5 and 6).
 */
#define _DEFAULT_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif

enum {
    STATUS_CHILD = 1,
    STATUS_COMMAND_LINE = 2,
    STATUS_NOT_PROCESS_1 = 3,
    STATUS_SYSTEM = 4,
    STATUS_NOT_STARTED = 127
};

static void fail(int status, const char *message)
{
    static const char prefix[] = "timing_waiter: ";
    char text[96];
    size_t length = sizeof prefix - 1;
    size_t count = strlen(message);
    ssize_t written;

    memcpy(text, prefix, length);
    memcpy(text + length, message, count);
    text[length + count] = '\n';
    written = write(2, text, length + count + 1);
    (void)written;
    _exit(status);
}

static void write_all(const char *text, size_t left)
{
    while (left > 0) {
        ssize_t written = write(1, text, left);

        if (written < 0 && errno == EINTR)
            continue;
        if (written <= 0)
            fail(STATUS_SYSTEM, "W5: cannot write to the standard output");
        text += written;
        left -= (size_t)written;
    }
}

#ifdef __linux__
/* Writes "\nwaiter_max_rss_kib <value>\n" into line and returns its length. */
static size_t value_line(char *line, long value)
{
    static const char keyword[] = "\nwaiter_max_rss_kib ";
    char digits[24];
    size_t count = 0;
    size_t length = sizeof keyword - 1;
    unsigned long magnitude = value < 0 ? 0UL - (unsigned long)value : (unsigned long)value;

    memcpy(line, keyword, length);
    do {
        digits[count++] = (char)('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude > 0);
    if (value < 0)
        line[length++] = '-';
    while (count > 0)
        line[length++] = digits[--count];
    line[length++] = '\n';
    return length;
}
#endif

int main(int argc, char **argv)
{
    struct rusage usage;
    pid_t child;
    pid_t reaped;
    int status;
    int flags;
    char line[64];
    size_t length;

    if (getpid() != 1)
        fail(STATUS_NOT_PROCESS_1, "W0: not process 1 of its PID namespace");
    if (argc < 2)
        fail(STATUS_COMMAND_LINE, "usage: timing_waiter <timing executable path> <argument>...");
#ifdef __linux__
    if (prctl(PR_SET_DUMPABLE, 0L, 0L, 0L, 0L) != 0)
        fail(STATUS_SYSTEM, "W1: cannot make the waiter not dumpable");
#endif

    child = fork();
    if (child < 0)
        fail(STATUS_SYSTEM, "W2: cannot fork");
    if (child == 0) {
        execv(argv[1], argv + 1);
        _exit(STATUS_NOT_STARTED);
    }

    do
        reaped = wait4(child, &status, 0, &usage);
    while (reaped < 0 && errno == EINTR);
    if (reaped != child)
        fail(STATUS_SYSTEM, "W3: cannot wait for the child");

    for (;;) {
        if (kill(-1, SIGKILL) != 0 && errno != ESRCH)
            fail(STATUS_SYSTEM, "W4: cannot signal the other processes");
        if (waitpid(-1, NULL, 0) >= 0)
            continue;
        if (errno == ECHILD)
            break;
        if (errno != EINTR)
            fail(STATUS_SYSTEM, "W4: cannot reap the other processes");
    }

    flags = fcntl(1, F_GETFL);
    if (flags < 0 || ((flags & O_NONBLOCK) != 0 && fcntl(1, F_SETFL, flags & ~O_NONBLOCK) != 0))
        fail(STATUS_SYSTEM, "W5: cannot make the standard output blocking");
#ifdef __linux__
    length = value_line(line, usage.ru_maxrss);
#else
    length = sizeof "\nwaiter_max_rss none\n" - 1;
    memcpy(line, "\nwaiter_max_rss none\n", length);
#endif
    write_all(line, length);

    return WIFEXITED(status) && WEXITSTATUS(status) == 0 ? 0 : STATUS_CHILD;
}

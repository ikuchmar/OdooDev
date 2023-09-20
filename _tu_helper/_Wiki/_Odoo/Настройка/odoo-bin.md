-d turbo -u base --i18n-overwrite  --dev=all

https://www.odoo.com/documentation/16.0/developer/reference/cli.html

python D:\Turbo\venv\include\odoo-14.0\odoo-bin --help


Разрешить выполнение скриптов в повершел для текущего пользователя
Set-ExecutionPolicy -Scope CurrentUser Unrestricted


Імпортувати файл з перекладами за допомогою командного рядка:
$ cd ../custom_addons/school_lesson_6_3/i18n
$ odoo-bin -c /etc/odoo15-server.conf -d school \
--i18n-import="uk_UA.po" --lang=uk_UA --i18n-overwrite


Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit

  Common options:

    -c CONFIG, --config=CONFIG
                        specify alternate config file
    -s, --save          save configuration to ~/.odoorc (or to
                        ~/.openerp_serverrc if it exists)
    -i INIT, --init=INIT
                        install one or more modules (comma-separated list, use
                        "all" for all modules), requires -d
    -u UPDATE, --update=UPDATE
                        update one or more modules (comma-separated list, use
                        "all" for all modules). Requires -d.

    можно через запятую без пробела указывать несколько модулей


    --without-demo=WITHOUT_DEMO
                        disable loading demo data for modules to be installed
                        (comma-separated, use "all" for all modules). Requires
                        -d and -i. Default is none
    -P IMPORT_PARTIAL, --import-partial=IMPORT_PARTIAL
                        Use this for big data importation, if it crashes you
                        will be able to continue at the current state. Provide
                        a filename to store intermediate importation states.
    --pidfile=PIDFILE   file where the server pid will be stored
    --addons-path=ADDONS_PATH
                        specify additional addons paths (separated by commas).
    --upgrade-path=UPGRADE_PATH
                        specify an additional upgrade path.
    --load=SERVER_WIDE_MODULES
                        Comma-separated list of server-wide modules.
    -D DATA_DIR, --data-dir=DATA_DIR
                        Directory where to store Odoo data

  HTTP Service Configuration:
    --http-interface=HTTP_INTERFACE
                        Listen interface address for HTTP services. Keep empty
                        to listen on all interfaces (0.0.0.0)
    -p PORT, --http-port=PORT
                        Listen port for the main HTTP service
    --longpolling-port=PORT
                        Listen port for the longpolling HTTP service
    --no-http           Disable the HTTP and Longpolling services entirely
    --proxy-mode        Activate reverse proxy WSGI wrappers (headers
                        rewriting) Only enable this when running behind a
                        trusted web proxy!

  Web interface Configuration:
    --db-filter=REGEXP  Regular expressions for filtering available databases
                        for Web UI. The expression can use %d (domain) and %h
                        (host) placeholders.

  Testing Configuration:
    --test-file=TEST_FILE
                        Launch a python test file.
    --test-enable       Enable unit tests.
    --test-tags=TEST_TAGS
                        Comma-separated list of specs to filter which tests to
                        execute. Enable unit tests if set. A filter spec has
                        the format: [-][tag][/module][:class][.method] The '-'
                        specifies if we want to include or exclude tests
                        matching this spec. The tag will match tags added on a
                        class with a @tagged decorator (all Test classes have
                        'standard' and 'at_install' tags until explicitly
                        removed, see the decorator documentation). '*' will
                        match all tags. If tag is omitted on include mode, its
                        value is 'standard'. If tag is omitted on exclude
                        mode, its value is '*'. The module, class, and method
                        will respectively match the module name, test class
                        name and test method name. Example: --test-tags
                        :TestClass.test_func,/test_module,external Filtering
                        and executing the tests happens twice: right after
                        each module installation/update and at the end of the
                        modules loading. At each stage tests are filtered by
                        --test-tags specs and additionally by dynamic specs
                        'at_install' and 'post_install' correspondingly.
    --screencasts=DIR   Screencasts will go in DIR/{db_name}/screencasts.
    --screenshots=DIR   Screenshots will go in DIR/{db_name}/screenshots.
                        Defaults to
                        C:\Users\IF1FE~1.KUC\AppData\Local\Temp\odoo_tests.

  Logging Configuration:
    --logfile=LOGFILE   file where the server log will be stored
    --syslog            Send the log to the syslog server
    --log-handler=PREFIX:LEVEL
                        setup a handler at LEVEL for a given PREFIX. An empty
                        PREFIX indicates the root logger. This option can be
                        repeated. Example: "odoo.orm:DEBUG" or
                        "werkzeug:CRITICAL" (default: ":INFO")
    --log-request       shortcut for --log-handler=odoo.http.rpc.request:DEBUG
    --log-response      shortcut for --log-
                        handler=odoo.http.rpc.response:DEBUG
    --log-web           shortcut for --log-handler=odoo.http:DEBUG
    --log-sql           shortcut for --log-handler=odoo.sql_db:DEBUG
    --log-db=LOG_DB     Logging database
    --log-db-level=LOG_DB_LEVEL
                        Logging database level
    --log-level=LOG_LEVEL
                        specify the level of the logging. Accepted values:
                        ['info', 'debug_rpc', 'warn', 'test', 'critical',
                        'runbot', 'debug_sql', 'error', 'debug',
                        'debug_rpc_answer', 'notset'].

  SMTP Configuration:
    --email-from=EMAIL_FROM
                        specify the SMTP email address for sending email
    --smtp=SMTP_SERVER  specify the SMTP server for sending email
    --smtp-port=SMTP_PORT
                        specify the SMTP port
    --smtp-ssl          if passed, SMTP connections will be encrypted with SSL
                        (STARTTLS)
    --smtp-user=SMTP_USER
                        specify the SMTP username for sending email
    --smtp-password=SMTP_PASSWORD
                        specify the SMTP password for sending email

  Database related options:
    -d DB_NAME, --database=DB_NAME
                        specify the database name
    -r DB_USER, --db_user=DB_USER
                        specify the database user name
    -w DB_PASSWORD, --db_password=DB_PASSWORD
                        specify the database password
    --pg_path=PG_PATH   specify the pg executable path
    --db_host=DB_HOST   specify the database host
    --db_port=DB_PORT   specify the database port
    --db_sslmode=DB_SSLMODE
                        specify the database ssl connection mode (see
                        PostgreSQL documentation)
    --db_maxconn=DB_MAXCONN
                        specify the maximum number of physical connections to
                        PostgreSQL
    --db-template=DB_TEMPLATE
                        specify a custom database template to create a new
                        database

  Internationalisation options. :
    Use these options to translate Odoo to another language. See i18n
    section of the user manual. Option '-d' is mandatory. Option '-l' is
    mandatory in case of importation

    --load-language=LOAD_LANGUAGE
                        specifies the languages for the translations you want
                        to be loaded
    -l LANGUAGE, --language=LANGUAGE
                        specify the language of the translation file. Use it
                        with --i18n-export or --i18n-import
    --i18n-export=TRANSLATE_OUT
                        export all sentences to be translated to a CSV file, a
                        PO file or a TGZ archive and exit
    --i18n-import=TRANSLATE_IN
                        import a CSV or a PO file with translations and exit.
                        The '-l' option is required.
    --i18n-overwrite    overwrites existing translation terms on updating a
                        module or importing a CSV or a PO file.
    --modules=TRANSLATE_MODULES
                        specify modules to export. Use in combination with
                        --i18n-export

  Security-related options:
    --no-database-list  Disable the ability to obtain or view the list of
                        databases. Also disable access to the database manager
                        and selector, so be sure to set a proper --database
                        parameter first

  Advanced options:
    --dev=DEV_MODE      Enable developer mode. Param: List of options
                        separated by comma. Options : all,
                        [pudb|wdb|ipdb|pdb], reload, qweb, werkzeug, xml
    --shell-interface=SHELL_INTERFACE
                        Specify a preferred REPL to use in shell mode.
                        Supported REPLs are: [ipython|ptpython|bpython|python]
    --stop-after-init   stop the server after its initialization
    --osv-memory-count-limit=OSV_MEMORY_COUNT_LIMIT
                        Force a limit on the maximum number of records kept in
                        the virtual osv_memory tables. The default is False,
                        which means no count-based limit.
    --transient-age-limit=TRANSIENT_AGE_LIMIT
                        Time limit (decimal value in hours) records created
                        with a TransientModel (mosly wizard) are kept in the
                        database. Default to 1 hour.
    --osv-memory-age-limit=OSV_MEMORY_AGE_LIMIT
                        Deprecated alias to the transient-age-limit option
    --max-cron-threads=MAX_CRON_THREADS
                        Maximum number of threads processing concurrently cron
                        jobs (default 2).
    --unaccent          Try to enable the unaccent extension when creating new
                        databases.
    --geoip-db=GEOIP_DATABASE
                        Absolute path to the GeoIP database file.

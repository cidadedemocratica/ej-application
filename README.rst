.. image:: https://api.codeclimate.com/v1/badges/fd8f8c7d5d2bc74c38df/maintainability
   :target: https://codeclimate.com/github/ejplatform/ej-server/maintainability
   :alt: Maintainability
.. image:: https://codecov.io/gh/ejplatform/ej-server/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/ejplatform/ej-server
.. image:: https://gitlab.com/ejplatform/ej-server/badges/master/pipeline.svg
    :target: https://gitlab.com/ejplatform/ej-server/commits/master


===========
EJ Platform
===========

You can visit EJ website at https://ejplatform.org.

Getting started
===============

Local development (Docker)
------------------------------

First clone the repository::

    $ git clone https://gitlab.com/pencillabs/ej/ej-server
    $ cd ej-server

The recomended way to run EJ is with Docker. With it 
you can quickly start the development server using the
commands::

    $ sudo pip3 install invoke==1.4.1 --user
    $ inv docker up

This will deploy EJ using **docker/docker-compose.yml** file.
Every change made on the repository will be reflected inside the
`docker_server` container.

You can access the running instance accessing `http://localhost:8000`.

Documentation
-------------

Documentation can be updated with::

    $ inv docs 
    
will be available at the ``build/docs/`` directory.

------

with docker:

    $ inv docker exec -c "inv docs"

Changing theme
--------------

The previous commands build EJ using the "default" theme. EJ accepts additional
themes and currently comes pre-installed with the alternate "cpa" theme. The
first step is to rebuild static assets::

    $ inv js db-assets
    $ inv sass -t cpa 

Now run the server using the --theme flag::

    $ inv run -t cpa

Tests
-----

If you are making changes to EJ codebase, do not forget to run tests frequently.
EJ uses Pytest_::

    $ inv test

------

with docker:

    $ inv docker exec -c "inv test"

.. _Pytest: https://docs.pytest.org/

Docker bash
-----------

You probably will want to execute commands inside the container.
It is possible to open a bash shell in the main "web" container with::

    $ inv docker run

You also can execute commands without open docker bash shell::

    $ inv docker exec -c " command "

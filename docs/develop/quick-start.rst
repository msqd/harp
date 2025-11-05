Quick start
===========

Get started with HARP in under 2 minutes using ``uvx`` - no installation required.


Your first proxy
:::::::::::::::::

.. code:: shell

    # Create a simple configuration file
    cat > config.yml << EOF
    proxy:
      endpoints:
        - name: httpbin
          port: 4000
          url: "https://httpbin.org/"
    EOF

    # Run HARP
    uvx --python 3.13 harp-proxy server --file config.yml

Visit http://localhost:4000/get to see your proxy in action.


What's next?
::::::::::::

**Configuration-based customization** (most common)
  Start here if you want to add features without writing code.
  See :doc:`customize` for configuration options, or explore the :doc:`configuration guide </operate/configure/index>`.

**Custom code and applications**
  Need to write Python code for custom logic? Generate a project:

  .. code:: shell

      uvx --python 3.13 harp-proxy create project

  See :doc:`run` for project structure and development workflows.

**Production deployment**
  Ready to deploy? See the :doc:`operator's guide </operate/index>`.

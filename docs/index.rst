The Dal.io Documentation
========================

Table of Contents
=================

.. toctree::
    :maxdepth: 1
    :caption: Beginner's Guide

    beginners-guide

.. toctree::
    :maxdepth: 1
    :caption: Developer's Guide

    developers-guide

.. toctree::
    :maxdepth: 2
    :caption: Modules

    modules

Index
=====

.. toctree::
    :maxdepth: 1

    index

.. _introduction:

Introduction
============
Dal-io is a financial modeling package for python aiming to facilitate the gathering, wrangling and analysis of financial data. The library uses **graphical object structures** and **progressive display of complexity** to make workflows suit the user's specific proficiency in python without making efficiency
sacrifices. 

The core library implements common workflows from well-supported packages and the means to flexibly interlink them, and aims to continue adding relevant features. However, the user is not constrained by these features, and is free to extend pieces through inheritance in order to implement extra functionality that can be used with the rest of the package. See :ref:`developers_guide` for more information on extending core features.

.. _instalation:

Installation
============
You can clone this repository from git using

.. code-block:: text

    git clone https://github.com/renatomatz/Dal-io

If you are using Windows, make sure you are in the package folder to use the functionality and that you run the following command before importing the modules.

.. code-block:: python

    import sys
    sys.path.append("/path-to-dalio/Dal-io") 

For Linux and Mac, you can access the package contents from your python environment anywhere with

.. code-block:: text

    export PYTHONPATH=$PYTHONPATH:"path/to/Dal-io"


.. _a_guided_example:

A Guided Example
================
Let's go through a quick example of what Dal-io can do. We'll build a simple portfolio optimization workflow and test it out with some sample stocks.

This example will be fairly dry, so if you want to jump right into it with some understanding of the Dal-io mechanics, you can go through the :ref:`beginners_guide` first. If you just want to see what the library is capable of, let's get right to it.

We'll start off by importing the Dal-io pieces

.. code-block:: python

    import numpy as np

    import dalio.external as de
    import dalio.translator as dt
    import dalio.pipe as dp
    import dalio.model as dm
    import dalio.application as da

Specific pieces can also be imported individually, though for testing this sub-module import structure is preferred.

Now lets set up our stock data input from Yahoo! Finance.

.. code-block:: python

    tickers = ["GOOG", "MSFT", "ATVI", "TTWO", "GM", "FORD", "SPY"]
    
    stocks = dt.YahooStockTranslator()\
        .set_input(de.YahooDR())

Easy right? Notice that the stock input is composed of one external source (in this case :code:`de.YahooDR`) and one translator (:code:`dt.YahooStockTranslator`). This is the case for any input, with one piece getting raw data from an external source and another one translating it to a format friendly to Dal-io pieces. For more on formatting, go to :ref:`formatting`. 

Notice the :code:`.set_input` call that took in the YahooDR object. Every all translators, pipes, models and applications share this method that allows them to plug the output of another object as their own input. This idea of connecting different objects like nodes in a graph is at the core of the **graphical object design**.

At this point you can try out running the model with :code:`stocks.run(ticker=tickers)` which will get the OHLCV data for the ticker symbols assigned to :code:`tickers`, though you can specify any ticker available in Yahoo! Finance. Notice that the column names where standardized to be all lower-case with underscores (_) instead of spaces. This is performed as part of the translation step to ensure all imported data can be referenced with common string representations.

Now lets create a data processing pipeline for our input data.

.. code-block:: python

    time_conf = dp.DateSelect()

    close = dp.PipeLine(
        dp.ColSelect(columns="close"),
        time_conf
    )(stocks)

    annual_rets = close + \
        dp.Period("Y", agg_func=lambda x: x[-1]) + \
        dp.Change(strategy="pct_change")

    cov = dp.Custom(lambda df: df.cov(), strategy="pipe") \
        .with_input(annual_rets)

    exp_rets = annual_rets + dp.Custom(np.mean)

That was a bit more challenging! Let's take it step by step.

We started off defining a :code:`DateSelect` pipe (which we will use later) and passing it into a pipeline with other pipes to get a company's annual returns. Pipelines aggregate zero or more Pipe objects and pass in a common input through all of their transformations. This skips data integrity checking while still allowing users to control pipes inside the pipeline from the outside (as we will with :code:`time_conf`)

We then added a custom pipe that applies the np.mean function to the annual returns to get the expected returns for each stock.

Finally, we did the exact same thing but with a lambda that calls the pd.DataFrame internal method .cov() to get the dataframe's covariance. As we will be passing the whole dataframe to the function at once, we set the Custom strategy to "pipe".

Notice how we didn't use :code:`.set_input()` as we did before, that's because we utilized alternative ways of establishing this same node-to-node connection. 

We can connect nodes with:

    #. :code:`p1.set_input(p2)` set p1's input to p2.

    #. :code:`p1.with_input(p2)` create a copy of p1 and set its input to p2.

    #. :code:`p1(p2)` same as :code:`p1.with_input(p2)`.

    #. :code:`pL + p2` set p2 as the last transformation in the PipeLine pL.

Now let's set up our efficient frontier model, get the optimal weights and finally create our optimal portfolio model.

.. code-block:: python

    ef = dm.MakeEfficientFrontier(weight_bounds=(-0.5, 1)) \
        .set_input("sample_covariance", cov) \
        .set_input("expected_returns", exp_rets)

    weights = dp.OptimumWeights() \
        .set_piece("strategy", "max_sharpe", risk_free_rate=0.0) \
        .set_input(ef)

    opt_port = dm.OptimumPortfolio() \
        .set_input("weights_in", weights) \
        .set_input("data_in", close)

And those are two examples of Dal-io Models! As you can see, models can have multiple named inputs, which can be set the same way as you would in a pipe but also having to specify their name. You also saw an example of a Builder, which has pieces (that can be set with the :code:`.set_piece()`) method which allow for more modular flexibility when deciding characteristics of certain pipes or models.We could go into what each source and pieces represents, but that can be better done through the documentation.

Now, as a final step, lets graph the performance of the optimal portfolio.

.. code-block:: python

    graph = da.PandasXYGrapher(x=None, y="close", legend="upper_right") \
        .set_input("data_in", dp.Index(100)(opt_port)) \
        .set_output("data_out", de.PyPlotGraph(figsize=(12, 8)))

Additionally, you can change the time range of the whole model at any point using the :code:`time_conf` object we created all the way in the beginning. Below is an example of setting the dates from 2016 to 2020.

.. code-block:: python

    time_conf.set_start("2016-01-01")
    time_conf.set_end("2019-12-31")

And that's it! 

All that you have to do now is run the model with :code:`graph.run(ticker=tickers)` to 

    #. Get stock data from Yahoo! Finance

    #. Process data 

    #. Optimize portfolio weights

    #. Get an optimum portfolio

    #. Graph optimum portfolio

Which yields this figure:

.. image:: images/port_opt_cook_graph.png

Notice how this :code:`.run()` call was the same as you did all the way back when you only had your imported data. This method is also common to all translators, pipes, models and applications, and it gives you the piece's output. 

This means you can get information of any of the stages you created like this, and for any stock that you'd like. For example, we can run the :code:`weights` object we created to get the weights associated with the portfolio we just plotted.

.. code-block:: python

    weights.run(ticker=tickers)

.. code-block:: text

    {'GOOG': 0.45514,
     'MSFT': 0.82602,
     'ATVI': -0.49995,
     'TTWO': 0.29241,
     'GM': -0.43788,
     'FORD': 0.38413,
     'SPY': -0.01986}

Also, every time you run a set of stocks or time intervals, the new run will be automatically layered with the old one and indexed at 100, which can be great for comparing how multiple portfolios would have fared! To clear this, just re-define the graph.

Hope this example was enough to show how you can create clean and powerful models using just a few lines of code!

.. _next_steps:

Next Steps
==========

If you read and enjoyed the example above, that's great! Now comes the part where you get to understand its various pieces, workflows and internal logic for you to start creating your own models with Dal-io. 

A good first step, if you haven't already is reading the :ref:`beginners_guide`. 

If you understood these core concepts well and are ready for some more examples, check out the cookbook.

For those who want to adventure into creating your own pieces (and hopefully contributing to the library) can read the :ref:`developers_guide` as well as the :ref:`formatting`.

And as always, you can check the full breakdown of the modules with the ol' reliable :ref:`modules`.

.. _indices_and_tables:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

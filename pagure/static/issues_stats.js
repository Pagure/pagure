
issues_history_stats_plot = function(url, _b, _s) {
  var svg = d3.select("svg"),
      margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = $('#tags').width() - margin.left - margin.right,
      height = +svg.attr("height") - margin.top - margin.bottom,
      g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var parseTime = d3.timeParse("%Y-%m-%d");

  var x = d3.scaleTime()
      .rangeRound([0, width]);

  var y = d3.scaleLinear()
      .rangeRound([height, 0]);

  var area = d3.area()
      .x(function(d) { return x(d.date); })
      .y1(function(d) { return y(d.value); });

  function draw_graph(data) {

    x.domain(d3.extent(data, function(d) { return d.date; }));
    y.domain([0, d3.max(data, function(d) { return d.value; })]);
    area.y0(y(0));

    g.append("path")
        .datum(data)
        .attr("fill", "steelblue")
        .attr("d", area);

    g.append("g")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x));

    g.append("g")
        .call(d3.axisLeft(y))
      .append("text")
        .attr("fill", "#000")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", "0.71em")
        .attr("text-anchor", "end")
        .text("Open Issues");
  };

  d3.json(url, function(d) {
    var _out = new Array();
    for (var _d in d.stats) {
      var t = {};
      t.date = parseTime(_d.split('T', 1)[0]);
      t.value = d.stats[_d];
      _out.push(t);
    }
    draw_graph(_out);
    _b.show();
    _s.hide();
  });

};


issues_history_stats_plot = function(url, _b, _s) {
  var svg = d3.select("svg"),
      margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = $('#stats').width() - margin.left - margin.right,
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

wait_for_task = function(url, callback){
  $.get(url)
  .done(function(data){
    callback(data);
  })
  .fail(function(){
    window.setTimeout(wait_for_task(url, callback), 1000);
  })
}

show_commits_authors = function(data) {
  var _b = $("#data_stats");
  var _s = $("#data_stats_spinner");
  var html = '<p> Since ' + data.results[3] + ' there has been '
    + data.results[0] + ' commits found in this repo, from '
    + data.results[2] + ' contributors</p>\n'
    + '<div class="list-group">\n';
  for (key in data.results[1]){
    for (key2 in data.results[1][key]){
      entry = data.results[1][key][key2]
      html += '  <a class="list-group-item" href="'
        + view_commits_url.replace('---', entry[1]) + '">'
        + entry[0]
        + '<div class="pull-xs-right">' + key + ' commits</div>'
        + '</a>\n';
    }
  }
  html += '</div>';
  _b.html(html);
  _b.show();
  _s.hide();
}

commits_authors = function(url, _data) {
  $.post( url, _data )
  .done(function(data) {
    wait_for_task(data.url, show_commits_authors);
  })
  .fail(function(data) {
  })
};


show_commits_history = function(data) {
  var _b = $("#data_stats");
  var _s = $("#data_stats_spinner");

  var parseTime = d3.timeParse("%Y-%m-%d");

  var _out = data.results.map(function(x){
    var t = {};
    t.date = parseTime(x[0]);
    t.value = x[1];
    return t;
  })

  var svg = d3.select("svg"),
      margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = $('#stats').width() - margin.left - margin.right,
      height = +svg.attr("height") - margin.top - margin.bottom,
      g = svg.append("g").attr(
        "transform", "translate(" + margin.left + "," + margin.top + ")");

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
        .text("Number of commits");
  };

  draw_graph(_out);
  _b.show();
  _s.hide();
}

commits_history = function(url, _data) {
  $.post( url, _data )
  .done(function(data) {
    wait_for_task(data.url, show_commits_history);
  })
  .fail(function(data) {
  })
};

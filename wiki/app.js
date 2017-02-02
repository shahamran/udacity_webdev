const express = require('express');
const path = require('path');
const favicon = require('serve-favicon');
const logger = require('morgan');
const cookieParser = require('cookie-parser');
const bodyParser = require('body-parser');
const nunjucks = require('nunjucks');
const mongo = require('mongodb').MongoClient;
const mongoUrl = 'mongodb://ran:2912@ds135069.mlab.com:35069/udacity-wiki';

const index = require('./routes/index');
const users = require('./routes/users');
const login = require('./routes/login');
// const pages = require('./routes/pages');

const app = express();

// view engine setup
// app.set('views', path.join(__dirname, 'templates'));
app.set('view engine', 'html');
nunjucks.configure('views', {
    autoescape: true,
    express: app
});

// uncomment after placing your favicon in /public
//app.use(favicon(path.join(__dirname, 'public', 'favicon.ico')));
app.use(logger('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

// connect to mongodb
mongo.connect(mongoUrl, (err, db) => {
  if (err) {
    // if can't connect, continue without db
    console.log('Could not conned to mongodb\n');
  } else {
    console.log('Connected to mongodb\n');
    // make db available in other middleware
    app.use((req, res, next) => {
      req.db = db;
      next();
    });
  }
});

app.use(index);
app.use(login);
app.use('/users', users);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  let err = new Error('Not Found');
  err.status = 404;
  next(err);
});

// error handler
app.use(function(err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error',
             {message: res.locals.message,
              error: res.locals.error,
              title: "Error!"});
});

module.exports = app;

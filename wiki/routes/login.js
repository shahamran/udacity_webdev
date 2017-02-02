const express = require('express');
const router = express.Router();

/* GET Login page. */
router.get('/login', function(req, res, next) {
  res.render('login', { title: 'Login' });
});

/* GET Signup page */
router.get('/signup', function(req, res, next) {
  res.render('signup', { title: 'Sign Up'});
});

module.exports = router;

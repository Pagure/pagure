# coding=utf-8
"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Vivek Anand <vivekanand1101@gmail.com>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class TestStarProjectLib(tests.SimplePagureTest):
    ''' Test the star project feature of pagure '''

    def setUp(self):
        """ Set up the environnment for running each star project lib tests """
        super(TestStarProjectLib, self).setUp()
        tests.create_projects(self.session)

    def test_update_star_project(self):
        ''' Test the update_star_project endpoint of pagure.lib '''

        repo_obj = pagure.lib._get_project(self.session, 'test')
        # test with invalud Star object, should return None
        msg = pagure.lib.update_star_project(
            self.session,
            repo_obj,
            None,
            'pingou',
        )
        self.session.commit()
        self.assertEqual(msg, None)
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 0)

        # test starring the project
        repo_obj = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.update_star_project(
            self.session,
            repo_obj,
            '1',
            'pingou',
        )

        self.session.commit()
        self.assertEqual(msg, 'You starred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 1)

        # test unstarring the project
        repo_obj = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.update_star_project(
            self.session,
            repo_obj,
            '0',
            'pingou',
        )

        self.session.commit()
        self.assertEqual(msg, 'You unstarred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 0)

    def test_star_project(self):
        ''' Test the _star_project endpoint of pagure.lib '''

        # test with not all arguments present
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        repo_obj = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib._star_project(
            self.session,
            repo_obj,
            None
        )
        self.session.commit()
        self.assertEqual(msg, None)

        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._star_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You starred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 1)

    def test_unstar_project(self):
        ''' Test the _unstar_project endpoint of pagure.lib '''

        # test with not all arguments present
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        repo_obj = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib._unstar_project(
            self.session,
            repo_obj,
            None
        )
        self.session.commit()
        self.assertEqual(msg, None)

        # the user hasn't starred the project before
        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._unstar_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.assertEqual(msg, 'You never starred the project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 0)

        # star it for testing
        msg = pagure.lib._star_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You starred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 1)

        # the user starred and wishes to unstar
        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._unstar_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You unstarred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 0)

    def test_get_stargazer_obj(self):
        ''' Test the _get_stargazer_obj test of pagure.lib '''

        # star the project first
        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._star_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You starred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 1)

        # get the object now
        repo_obj = pagure.lib._get_project(self.session, 'test')
        star_obj = pagure.lib._get_stargazer_obj(
            self.session,
            repo_obj,
            user_obj
        )
        self.assertEqual(isinstance(star_obj, pagure.lib.model.Star), True)

        # unstar it and then try to get the object
        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._unstar_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You unstarred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 0)

        # we don't store if the user has unstarred, we delete the obj
        # so, we should get anything back in the query
        repo_obj = pagure.lib._get_project(self.session, 'test')
        star_obj = pagure.lib._get_stargazer_obj(
            self.session,
            repo_obj,
            user_obj
        )
        self.assertEqual(star_obj is None, True)

    def test_has_starred(self):
        ''' Test the has_starred endpoint of pagure.lib '''

        # star the project
        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._star_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You starred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 1)

        has_starred = pagure.lib.has_starred(
            self.session,
            repo_obj,
            'pingou'
        )
        self.assertEqual(has_starred is True, True)

        # unstar it and then test for has_starred
        repo_obj = pagure.lib._get_project(self.session, 'test')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        msg = pagure.lib._unstar_project(
            self.session,
            repo_obj,
            user_obj,
        )
        self.session.commit()
        self.assertEqual(msg, 'You unstarred this project')
        user_obj = pagure.lib.get_user(self.session, 'pingou')
        self.assertEqual(len(user_obj.stars), 0)

        # check now, it should return False
        has_starred = pagure.lib.has_starred(
            self.session,
            repo_obj,
            'pingou'
        )
        self.assertEqual(has_starred is False, True)


if __name__ == '__main__':
    unittest.main(verbosity=2)

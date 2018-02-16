import React, { Component } from 'react';

import CommentButton from './comment-button/comment-button';
import LikeButton from './like-button/like-button';
import RepostButton from './repost-button/repost-button';
import MessageButton from './message-button/message-button';

class SocialCard extends Component {
    constructor() {
        super();
    };

    render() {
        return (
            <div className='container-fluid mb-2'>
                <div className='row'>
                    <div className='col-3'>
                        <CommentButton />
                    </div>
                    <div className='col-3'>
                        <LikeButton />
                    </div>
                    <div className='col-3'>
                        <RepostButton />
                    </div>
                    <div className='col-3'>
                        <MessageButton />
                    </div>
                </div>
            </div>
        );
    };
};

export default SocialCard;
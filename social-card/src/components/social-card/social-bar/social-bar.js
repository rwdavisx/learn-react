import React, { Component } from 'react';

import CommentButton from './comment-button/comment-button';
import LikeButton from './like-button/like-button';
import RepostButton from './repost-button/repost-button';
import MessageButton from './message-button/message-button';

class SocialCard extends Component {
    constructor(props) {
        super(props);
        this.state = {
            comments: this.props.comments,
            likes: this.props.likes,
            reposts: this.props.reposts,
        }
    };

    render() {
        return (
            <div className='container-fluid p-2'>
                <div className='d-flex justify-content-between'>
                        <CommentButton num={this.state.comments}/>                   
                        <RepostButton num={this.state.likes}/>
                        <LikeButton num={this.state.likes}/>
                        <MessageButton />
                </div>
            </div>
        );
    };
};

export default SocialCard;
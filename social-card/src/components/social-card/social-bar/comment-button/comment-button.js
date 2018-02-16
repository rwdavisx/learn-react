import React, { Component } from 'react';
import {MdComment} from 'react-icons/lib/md';
import './comment-button.css';

class CommentButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
            amount: isNaN(this.props.num) || this.props.num === null ? 0 : this.props.num,
        }
    };

    render() {
        return (
            <div className={'comment-btn'}>
                <MdComment /><span>{this.state.amount}</span>
            </div>
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default CommentButton;
